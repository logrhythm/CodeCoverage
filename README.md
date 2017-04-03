# CodeCoverage
The CodeCoverage utility is used for generating code coverage reports for C++ repositories. Currently the following LogRhythm repositories can get code coverage measurements through this utility: 
* [StopWatch](https://github.com/LogRhythm/StopWatch)
* [Queuenado](https://github.com/LogRhythm/Queuenado)
* [FileIO](https://github.com/LogRhythm/FileIO)
* [DeathKnell](https://github.com/LogRhythm/DeathKnell)

## Usage example
```
git clone https://github.com/LogRhythm/FileIO
cd FileIO
/usr/local/probe/bin/CodeCoverage.py
```
This will generate the code coverage from the unit tests. The result will be stored in `FileIO/coverage/coverage_FileIO.html` which you can view in your browser


## Requirements
* cmake
* gcovr
* g++ 4.8 or newer