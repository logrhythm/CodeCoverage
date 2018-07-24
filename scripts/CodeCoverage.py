#!/usr/bin/env python

import os
import re
import sys
import argparse
import shutil
import zipfile
import ntpath
import subprocess
import os.path

DEFAULT_WHITELIST = ".*cpp$"
DEFAULT_BLACKLIST = "/usr/local/probe/.*"

CMAKEFILEPATH = "CMakeLists.txt"
LIBRARY_TO_BUILD_REGEX = 'SET\(LIBRARY_TO_BUILD (.*)\)$'

PROBE_BUILD = True

def get_file_content(filename):
    with open(filename) as filehandle:
        content = filehandle.readlines()
        return content

def get_library_to_build_name(line_str):
    match_obj = re.search(LIBRARY_TO_BUILD_REGEX, line_str, re.M|re.I)
    if match_obj:
        return True, match_obj.group(1)
    return False, ""

def get_project_name_from_CMakeLists_file(full_file_path):
    for line in get_file_content(filename=full_file_path):
        found, project_name = get_library_to_build_name(line_str=line)
        if found:
            return True, project_name
    return False, ""

def print_error_and_usage(argParser, error):
    print "Error:  " + error + "\n"
    print argParser.print_help()
    sys.exit(2)

def santize_input_args(arg_parser, args):
    if len(sys.argv) > 3:
        print_error_and_usage(argParser=arg_parser, error="Too many arguments supplied.")

def destroy_directory(dir_path):
    shutil.rmtree(dir_path)

def clean_and_build_directory(dir_path):
    if os.path.exists(dir_path):
        destroy_directory(dir_path=dir_path)
    os.makedirs(dir_path)

def remove_file_extension(filename):
    return os.path.splitext(filename)[0]

def strip_file_from_full_path(full_file_path):
    return ntpath.basename(full_file_path)

def unzip_file(full_file_path, directory_to_extract_to):
    to_unzip = zipfile.ZipFile(full_file_path, 'r')
    unzipped_dir_name = remove_file_extension(filename=strip_file_from_full_path(full_file_path=full_file_path))
    full_unzipped_dir_path = directory_to_extract_to + "/" + unzipped_dir_name
    if os.path.exists(full_unzipped_dir_path):
        destroy_directory(full_unzipped_dir_path)
    to_unzip.extractall(directory_to_extract_to)
    to_unzip.close()



def get_gcov():
    if PROBE_BUILD:
        return '--gcov-executable /usr/local/gcc/bin/gcov'
    return '--gcov-executable gcov'

def get_gcovr():
    if PROBE_BUILD:
        return '/usr/local/probe/bin/gcovr'
    return 'gcovr'

def run_gcovr(project_name, whitelist_filter, blacklist_filter):
    GCOVR = get_gcovr()
    VERBOSE = '--verbose'
    SORT_PERCENTAGE = '--sort-percentage'
    FILTER = '--filter=\"'+whitelist_filter+'\"'
    EXCLUDE = '--exclude=\"'+blacklist_filter+'\"'
    GCOV_EXE = get_gcov()
    EXCLUDE_UNREACHABLE = '--exclude-unreachable-branches'
    HTML_FLAGS = '--html --html-details'   
    OUTPUT_FILE = '-o coverage_' + project_name + '.html'
    FLAGS = VERBOSE + ' ' + SORT_PERCENTAGE + ' ' + FILTER + ' ' + EXCLUDE + ' ' + GCOV_EXE + ' ' + EXCLUDE_UNREACHABLE + ' ' + HTML_FLAGS
    GCOVR_CMD_STR = GCOVR + ' ' + FLAGS + ' '  + OUTPUT_FILE
    try:
        ret_code = subprocess.check_call([GCOVR_CMD_STR], stderr=subprocess.STDOUT, shell=True)
        print "Gcovr process return code: " + str(ret_code)
    except:
        print "ERROR: Gcovr process failed! : \n" + GCOVR_CMD_STR
        sys.exit(1)

def copy_coverage_files_into_cov_dir(launch_dir, rpmbuild_dir):
    cov_files = ''
    for root, dirs, files in os.walk(rpmbuild_dir):
        if 'UnitTestRunner.dir' in root or 'gtest' in root:
            continue
        for filename in files:
           if filename.endswith('.gcda') or filename.endswith('.gcno'):
              cov_files += (os.path.join(root, filename) + ' ')

    
    CP_COV_FILES_STR = 'cp -n ' + cov_files + ' ' + launch_dir + '/coverage'

    try:
        ret_code = subprocess.check_call([CP_COV_FILES_STR], stderr=subprocess.STDOUT, shell=True)
        print "Copy coverage files into coverage directory return code: " + str(ret_code)
    except:
        print "ERROR: Copy coverage files into coverage directory failed!"
        sys.exit(1)

def format_user_list(user_list):
    formatted_list = None
    if user_list is not None:
        for whitelist_item in user_list.split():
            print "Split into : " + whitelist_item
            if formatted_list is None:
                formatted_list = '.*' + whitelist_item + '$'
            else:
                formatted_list = formatted_list + '|.*'+whitelist_item+'$'
    return formatted_list

def generate_gcovr_filter(formatted_user_list, default_list):
    if formatted_user_list is None:
        return default_list
    else:
        return default_list + '|' + formatted_user_list

def main(argv):
    argParser = argparse.ArgumentParser(description="Generate code coverage information for a Network Monitor repository that uses CMake")
    argParser.add_argument("-w",
                           "--whitelist",
                           dest="whitelist",
                           metavar="HEADER_FILE",
                           help="Whitelist a header or template file for code coverage")
    argParser.add_argument("-b",
                           "--blacklist",
                           dest="blacklist",
                           metavar="SOURCE_FILE",
                           help="Blacklist a source file for code coverage")

    args = argParser.parse_args()
    santize_input_args(arg_parser=argParser, args=args)
  
    found_project_name, project_name = get_project_name_from_CMakeLists_file(full_file_path=CMAKEFILEPATH)
    if not found_project_name:
        print "ERROR: No project name found in CMakeLists.txt"
        sys.exit(2)   

    LAUNCH_DIR = os.getcwd()
    PROJECT = project_name
    HOME_DIR = os.path.expanduser('~')
    RPMBUILD_DIR = HOME_DIR + '/rpmbuild/BUILD/' + PROJECT
    USER_WHITELIST = None
    USER_BLACKLIST = None
    GTEST_ZIP_PATH = LAUNCH_DIR + '/thirdparty/gtest-1.7.0.zip'
    global PROBE_BUILD
    global DEFAULT_BLACKLIST
    if os.path.exists("/usr/local/probe/bin/cmake"):
        PROBE_BUILD=True
        print "Using /usr/local/probe as the default path"
    else: 
       PROBE_BUILD=False
       print "Using /usr/local/ as the default path"
       DEFAULT_BLACKLIST = "/usr/local/.*"



    if args.whitelist:
        USER_WHITELIST = args.whitelist
        print "USER_WHITELIST = " + USER_WHITELIST
    if args.blacklist:
        USER_BLACKLIST = args.blacklist
        print "USER_BLACKLIST = " + USER_BLACKLIST

    unzip_file(full_file_path=GTEST_ZIP_PATH, directory_to_extract_to="thirdparty")
    clean_and_build_directory(dir_path="coverage")
    os.chdir(LAUNCH_DIR + '/coverage')

    gcovr_whitelist = generate_gcovr_filter(formatted_user_list=format_user_list(user_list=USER_WHITELIST),
                                            default_list=DEFAULT_WHITELIST)
    gcovr_blacklist = generate_gcovr_filter(formatted_user_list=format_user_list(user_list=USER_BLACKLIST),
                                            default_list=DEFAULT_BLACKLIST)

    # ProbeTransmogrifier builds both Probe_Transmogrifier and ProbeTransmogrifier. ProbeTransmogrifier has the code we want to cover, not Probe_Transmogrifier
    if PROJECT == 'Probe_Transmogrifier':
       RPMBUILD_DIR = HOME_DIR + '/rpmbuild/BUILD/' + 'ProbeTransmogrifier'

    copy_coverage_files_into_cov_dir(launch_dir=LAUNCH_DIR, rpmbuild_dir=RPMBUILD_DIR)
    run_gcovr(project_name=PROJECT,
              whitelist_filter=gcovr_whitelist,
              blacklist_filter=gcovr_blacklist)

if __name__ == '__main__':
    main(sys.argv[1:])
