# Introduction

This is a collection of smaller programs and scripts to display "inline" in [Adafruit Learning System][learn] guides.

Adafruit is an Open Source company. To support Adafruit, please consider buying products at [adafruit.com](https://www.adafruit.com/).

Starting in 2023, guides using a specific Adafruit board will be placed in a subdirectory with that product name to reduce the number of directories under the main directory. If you are creating a new guide, please check if your Adafruit board falls into one of these groups and make your project code directory in the appropriate subfolder.

* Flora/
* ItsyBitsy/
* MagTag/
* MEMENTO/
* NeoTrellis/
* PyLeap/
* PyPortal/
* QTPy/

## Issues

Issues with guides should be reported in the guide itself under "Feedback? Corrections?"

## Make Your Own Guides

This repo is only for Adafruit approved Learning System Guides. If you'd like to write your own guide, see [Create your own content with Adafruit Playground!](https://learn.adafruit.com/adafruit-playground-notes).

## Contributing and Testing

For details on contributing for Adafruit approved guides, see the guide [Contribute to the Adafruit Learning System with Git and GitHub](https://learn.adafruit.com/contribute-to-the-adafruit-learning-system-with-git-and-github) and [Contribute to CircuitPython with Git and GitHub](https://learn.adafruit.com/contribute-to-circuitpython-with-git-and-github/github-personal-access-token).

The code here is checked by GitHub Actions against Pylint (for CircuitPython code) or the Arduino compilation process.

Code in directories containing a file called `.circuitpython.skip` will be skipped by Pylint checks.

Code in directories containing a `.[platformname].test` file, such as `.uno.test` will be compiled against the corresponding platform.

[learn]: https://learn.adafruit.com/

## Running pylint locally
Install a specific version of pylint under the name "pylint-learn":
```
pip install pipx
pipx install --suffix=-learn pylint==2.7.1
```
Then use the `pylint_check` script to run pylint on the files or directories
of your choice (note that your terminal *must* be in the top directory of
Adafruit_Learning_System_Guides, not a sub-directory):
```
./pylint_check CircuitPython_Cool_Project
```
## Licensing

Adafruit Learning System code files should have author and license information conforming to the open [SPDX specification](https://www.iso.org/standard/81870.html).
See [this page](https://learn.adafruit.com/contribute-to-the-adafruit-learning-system-with-git-and-github/add-author-and-license-information) for more.

Updated November 29, 2023
