"""Script to add user and hashed password to
authorized_user.db sqlite3 database"""

import sqlite3
from werkzeug.security import generate_password_hash
from getpass import getpass


# Connect to sqlite3 db
connection = sqlite3.connect("authorized_users.db")
cursor = connection.cursor()

# Prompt for username and password 
username = input("User name to add: ").strip()

password1 = getpass()
print("...and again")
password2 = getpass()
while password1 != password2:
    print("\nPasswords do not match. Please try again: ")
    password1 = getpass()
    password2 = getpass()
pwd = password1
pwd_hash = generate_password_hash(pwd)

print(len(pwd_hash))

# Write username and hashed pwd to db 
cursor.execute("INSERT INTO users VALUES (?,?)",(username,pwd_hash))

connection.commit()
connection.close()

# From command line open db as 'sqlite3 name.db';
# view tables with '.tables' and view content with
# 'SELECT * FROM tablename'.

# columns are userid, pwd

