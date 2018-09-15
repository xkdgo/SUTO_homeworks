#!/usr/local/bin/python3
# -*- coding: utf-8; -*-

import gzip
import datetime
import os
import re
from collections import namedtuple
import json
import argparse
import logging
from statistics import median


def init_config(config_filename=None):
    # default config
    initial_config = {
        "LOG_DIR": "./log",
        "REPORT_DIR": "./reports",
        "REPORT_SIZE": 1000,
        "REPORT_TEMPLATE": "./templates/report.html",
        # "REPORT_LOG": "./log_analyzer.log",
        "PARSE_ERROR_PERC_MAX": 0.1,
        "DEBUG": False
    }
    if config_filename:
        try:
            with open(config_filename, 'rb') as conf_file:
                try:
                    new_config_args = json.load(conf_file, encoding='utf-8')
                    logging.info(new_config_args)
                    initial_config.update(new_config_args)
                except json.decoder.JSONDecodeError:
                    logging.info("cant decode config file %s" % config_filename)
                    raise RuntimeError("Invalid fileformat need JSON")

        except FileNotFoundError:
            logging.info("file %s not found" % config_filename)
            raise RuntimeError("Invalid filepath to config file")
    return initial_config


def catchfile(directory):
    Logfile = namedtuple('Logfile', 'path date ext')
    latest_file = None
    regexline = r"^(?:nginx-access-ui).*?(?P<log_time>\d{8})\.(?P<ext>log|gz)$"
    regex = re.compile(regexline)
    # check directory
    if not os.path.isdir(directory):
        raise RuntimeError("Wrong directory name %s" % directory)
    if not os.listdir(directory):
        logging.debug("Could not find a logfile in empty directory %s" % directory)
        return
    for file in os.listdir(directory):
        path = os.path.join(directory, file)
        if not os.path.isfile(path):
            continue
        match = regex.match(file)
        if not match:
            continue
        candidate_file = Logfile(path, match.group('log_time'), match.group('ext'))
        try:
            if not latest_file or str_to_datetime(candidate_file.date) > str_to_datetime(latest_file.date):
                latest_file = candidate_file
            else:
                continue
        except ValueError:
            continue
    logging.debug("Found latest file %s" % latest_file.path)
    return latest_file


def str_to_datetime(date_str):
    format_str = '%Y%m%d'
    datetime_obj = datetime.datetime.strptime(date_str, format_str)
    return datetime_obj


def nginx_log_parser(line):
    logpats = r'^\S+.*?\[\S+\s\S+\]\s+\"\S+\s+(?P<request_url>\S+).*?(?P<response_time>\S+)$'
    logpat = re.compile(logpats)
    log = {}
    match = logpat.match(line.rstrip())
    if match:
        log['request_url'] = match.group('request_url')
        log['response_time'] = match.group('response_time')
    else:
        raise RuntimeWarning("Error matching line %s" % line)
    log['response_time'] = float(log['response_time']) if log['response_time'] != '-' else 0
    return log


def process_lines_in_file(filecatcher_result_f):
    with gzip.open(filecatcher_result_f.path, 'rb') if filecatcher_result_f.ext == "gz" else open(
            filecatcher_result_f.path, 'rb') as file_item:
        for line in file_item:
            try:
                yield (nginx_log_parser(line.decode('utf-8'))), None
            except RuntimeWarning as err_process_lines_in_file:
                yield None, err_process_lines_in_file


def process_and_count_statistics_from_file_lines(filecatcher_result_process, error_ratio=0.2):
    logging.info("Started process file")
    line_counter = 0
    err_counter = 0
    parsed_counter = 0
    total_response_time = 0
    result_dict = {}
    # form result_dict
    for line, err_process in process_lines_in_file(filecatcher_result_process):
        line_counter += 1
        if line:
            parsed_counter += 1
            statistic_dict = result_dict.get(line['request_url'],
                                             {'request_url': line['request_url'],
                                              'count': 0, 'time_sum': 0.0, 'time_max': 0.0, 'time_list': []})
            statistic_dict['count'] += 1
            statistic_dict['time_list'].append(line['response_time'])
            statistic_dict['time_sum'] += line['response_time']
            statistic_dict['time_max'] = line['response_time'] \
                if line['response_time'] > statistic_dict['time_max'] else statistic_dict['time_max']
            total_response_time += line['response_time']
            result_dict[line['request_url']] = statistic_dict
        elif err_process:
            err_counter += 1
            logging.debug(err_process)
    logging.info("total line counter %s\n"
                 "parsed counter %s\n"
                 "error counter %s\n"
                 "total_time counter %s" % (line_counter,
                                            parsed_counter,
                                            err_counter,
                                            total_response_time))
    # Count err_percentage if exceeds limit raise Exception
    if float(parsed_counter) / line_counter < (1.0 - error_ratio):
        logging.info('Wrong format. %d of %d lines parsed. '
                     'More than %d%% of errors - failed parsing',
                     parsed_counter, line_counter,
                     int(error_ratio * 100))
        raise RuntimeError('Wrong format, '
                           '%d of %d lines parsed. '
                           ', More than %d%% of errors - failed parsing' % (parsed_counter,
                                                                            line_counter,
                                                                            int(error_ratio * 100)))
    # count median, percent etc in result_dict
    for url_key in result_dict.keys():
        result_dict[url_key]['time_med'] = median(result_dict[url_key].pop('time_list'))
        result_dict[url_key]['time_perc'] = result_dict[url_key]['time_sum'] * 100 / total_response_time
        result_dict[url_key]['count_perc'] = result_dict[url_key]['count'] * 100 / parsed_counter
        result_dict[url_key]['time_avg'] = result_dict[url_key]['time_sum'] / result_dict[url_key]['count']
    logging.info("End process file")
    return list(result_dict.values())


def format_and_sort_to_json(result_table, report_size=1000):
    return json.dumps(sorted(result_table, key=lambda k: k['time_sum'], reverse=True)[:report_size])


def json_render(jsontable, htmlfile_template_path):
    from string import Template
    with open(htmlfile_template_path, 'rb') as htmlfile_path:
        s = htmlfile_path.read().decode("utf-8")
        s = Template(s)
        r = s.safe_substitute(table_json=jsontable)
        return r


def main(config_dict):
    try:
        filecatcher_result = catchfile(config_dict.get("LOG_DIR", "."))
    except Exception as err_file:
        logging.debug(err_file)
        return
    if not filecatcher_result:
        return
    report_path_dir = config_dict.get("REPORT_DIR", ".")
    report_file_name = 'report_%s.html' % filecatcher_result.date
    report_result = os.path.join(report_path_dir, report_file_name)
    if os.path.isfile(report_result):
        print("Report %s already done" % report_result)
        logging.info("Report %s already done" % report_result)
        return
    try:
        result_list = process_and_count_statistics_from_file_lines(filecatcher_result,
                                                                   config_dict.get("PARSE_ERROR_PERC_MAX"))
    except Exception as err_result_list:
        logging.debug(err_result_list)
        return

    try:
        result_json_table = format_and_sort_to_json(
            result_list, config_dict.get("REPORT_SIZE", 1000))
    except Exception as err_format_json:
        logging.debug(err_format_json)
        return

    if not os.path.isdir(report_path_dir):
        os.makedirs(report_path_dir)
    with open(report_result, 'w') as f:
        f.write(json_render(result_json_table, config_dict.get("REPORT_TEMPLATE")))
    print("You can find report at  %s" % report_result)
    logging.info("You can find report at  %s" % report_result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Config JSON file path", default=None)
    args = parser.parse_args()
    config = init_config(args.config)
    logging.basicConfig(filename=config.get("REPORT_LOG", None),
                        level=logging.DEBUG if config.get("DEBUG", None) else logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')
    logging.info('START INFO logging')
    logging.debug('START DEBUG logging')
    logging.debug("get config parameters %s" % config)
    try:
        main(config)
    except KeyboardInterrupt as err:
        logging.exception("CTRL+C %s" % err)
    except Exception as err:
        logging.exception("UNHANDLED ERROR %s" % err)
