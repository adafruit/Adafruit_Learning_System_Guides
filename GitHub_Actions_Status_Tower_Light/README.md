# GitHub Actions Status Tower Light

This project allows you to see the status of your current Actions run on a repo of your choice,
lit up on a tower light plugged into your computer via USB. The program is run directly from your
computer.

This README includes the basic requirements to run the project. Check out
[the guide](https://learn.adafruit.com/github-actions-status-tower-light) for details.

### Four requirements to run this example:
#### Hardware:
* [Tri-Color USB Controller Tower Light with Buzzer](https://www.adafruit.com/product/5125)
#### Software:
* Python
#### Libraries to `pip install`:
* `pyserial`
* `requests`
#### Create GitHub API token:
* In your GitHub account, click through Settings > Developer Settings > Personal Access Tokens,
  and generate a new token with no scopes.
* Create an environment variable on your computer and make it available for your code to use.

To begin, plug the tower light into a USB port on your computer.

This project is written in Python. To use, prepare the requirements above, copy the `.py` file t
your computer, and run the file as follows, updating `filename.py` to the name you chose for the
file:

`python filename.py`