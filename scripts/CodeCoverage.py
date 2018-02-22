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


def get_cmake(): 
    if PROBE_BUILD:
        print "using /usr/local/probe/bin/cmake"
        return '/usr/local/probe/bin/cmake'
    return 'cmake'

def get_make_arguments():
    default_args = '-DCMAKE_CXX_COMPILER_ARG1:STRING=\'-std=c++14 -Wall -Werror -g -gdwarf-2 -fno-elide-constructors -fprofile-arcs -ftest-coverage -O0 -fPIC -m64  -fno-inline -fno-inline-small-functions -fno-default-inline '
    if PROBE_BUILD:
        default_args += ' -Wl,-rpath -Wl,. -Wl,-rpath -Wl,/usr/local/probe/lib -Wl,-rpath -Wl,/usr/local/probe/lib64 '
    default_args += '\''
    return default_args

def get_compiler():
    if PROBE_BUILD:
        return '-DCMAKE_CXX_COMPILER=/usr/local/probe/bin/g++'
    return 'g++'

def run_cmake_cmd():
    CMAKE = get_cmake()
    DEBUG_FLAG = '-DUSE_LR_DEBUG=ON'
    VERSION_FLAG = '-DVERSION=' + str(1)
    ARG1_FLAGS = get_make_arguments()
    COMPILER_EXE_FLAG =  get_compiler()
    CMAKELISTS_DIR = '..'
    CMAKE_STR = CMAKE + ' ' + DEBUG_FLAG + ' ' + VERSION_FLAG + ' ' + ARG1_FLAGS + ' ' + COMPILER_EXE_FLAG + ' ' + CMAKELISTS_DIR
    CMAKE_CMD = [CMAKE_STR]
    try:
        ret_code = subprocess.check_call(CMAKE_CMD, stderr=subprocess.STDOUT, shell=True)
        print "CMake return code: " + str(ret_code)
    except:
        print "ERROR: CMake command failed!"
        sys.exit(1)

def compile_project():
    COMPILE_CMD = ['make -j8']
    try:
        ret_code = subprocess.check_call(COMPILE_CMD, stderr=subprocess.STDOUT, shell=True)
        print "Compile return code: " + str(ret_code)
    except:
        print "ERROR: Compile project failed!"
        sys.exit(1)

def run_UnitTestRunner(launch_dir):
    CP_RUNNER_SCRIPT = 'cp ' + launch_dir + '/scripts/unitTestRunner.sh ' + launch_dir + '/build'
    CP_RUNNER_SCRIPT_CMD = [CP_RUNNER_SCRIPT]
    ret_code = subprocess.check_call(CP_RUNNER_SCRIPT_CMD, stderr=subprocess.STDOUT, shell=True)
    print "Copy script return code: " + str(ret_code)
    RUNNER_SCRIPT_CMD = ['sh unitTestRunner.sh']
    try:
        ret_code = subprocess.check_call(RUNNER_SCRIPT_CMD, stderr=subprocess.STDOUT, shell=True)
        print "UnitTestRunner process return code: " + str(ret_code)
    except:
        # The script will not exit here, as some repos have tests that will
        #   inherently fail during code coverage (FileIO, ProbeTransmogrifier)
        print "ERROR: UnitTestRunner process failed!"

def get_gcovr():
    if PROBE_BUILD:
        return '/usr/local/probe/bin/gcovr'
    return 'gcovr'

def get_gcov():
    if PROBE_BUILD:
        return '--gcov-executable /usr/local/probe/bin/gcov'
    return '--gcov-executable gcov'


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

def copy_coverage_files_into_cov_dir(object_dir, launch_dir):
    CP_COV_FILES_STR = 'cp ' + launch_dir + '/build/CMakeFiles/' + object_dir + '/src/* ' + launch_dir +'/coverage'
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
    OBJ_DIR = PROJECT + '.dir'
    USER_WHITELIST = None
    USER_BLACKLIST = None
    GTEST_ZIP_PATH = LAUNCH_DIR + '/3rdparty/gtest-1.7.0.zip'
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

    unzip_file(full_file_path=GTEST_ZIP_PATH, directory_to_extract_to="3rdparty")

    clean_and_build_directory(dir_path="coverage")
    clean_and_build_directory(dir_path="build")

    os.chdir(LAUNCH_DIR + '/build')
    run_cmake_cmd()
    compile_project()
    run_UnitTestRunner(launch_dir=LAUNCH_DIR)
    os.chdir(LAUNCH_DIR + '/coverage')

    gcovr_whitelist = generate_gcovr_filter(formatted_user_list=format_user_list(user_list=USER_WHITELIST),
                                            default_list=DEFAULT_WHITELIST)
    gcovr_blacklist = generate_gcovr_filter(formatted_user_list=format_user_list(user_list=USER_BLACKLIST),
                                            default_list=DEFAULT_BLACKLIST)
    copy_coverage_files_into_cov_dir(object_dir=OBJ_DIR, launch_dir=LAUNCH_DIR)
    run_gcovr(project_name=PROJECT,
              whitelist_filter=gcovr_whitelist,
              blacklist_filter=gcovr_blacklist)

if __name__ == '__main__':
    main(sys.argv[1:])
