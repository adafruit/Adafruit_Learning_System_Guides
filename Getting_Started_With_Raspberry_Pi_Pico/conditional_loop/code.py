"""Example of assigning a variable, and comparing it to a value in a loop."""
user_name = input ("What is your name? ")

while user_name != "Clark Kent":
    print("You are not Superman - try again!")
    user_name = input ("What is your name? ")
print("You are Superman!")
