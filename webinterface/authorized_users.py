# -*- coding: utf-8 -*-
"""
@author: Steven Court
Script to add users and hashed passwords to the
authorized_user.db sqlite3 database. This db must
exist for users to access the interface.

Both the database and users table (userid, pwd) 
will be created if they do not already exist
"""

import sqlite3
from sqlite3 import Error
from werkzeug.security import generate_password_hash
from getpass import getpass


DB_PATH = "authorized_users.db"


def add_user():
    """Add user to database"""
    # Connect to sqlite3 db
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    # Prompt for username and password 
    username = input("User name to add: ").strip()
    # Check user does not exist
    cursor.execute('''SELECT userid FROM users WHERE userid=?''', (username,))
    data = cursor.fetchall()
    if data:
        print("USER ALREADY EXISTS, please choose another")
        #connection.close()
        add_user()
    else:
        password1 = getpass()
        #print("...and again")
        password2 = getpass()
        while password1 != password2:
            print("PASSWORDS DO NOT MATCH, please try again: ")
            password1 = getpass()
            password2 = getpass()
        pwd = password1
        pwd_hash = generate_password_hash(pwd)
        # Write username and hashed pwd to db 
        cursor.execute("INSERT INTO users VALUES (?,?)",(username,pwd_hash))
        connection.commit()
        connection.close()
        print("User successfully added!")


def view_users():
    """Print all current userids to terminal"""
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute('''SELECT * FROM users;''')
    data=cursor.fetchall()
    print("\nCurrent users:")
    for u in data:
        print(" ",u[0])
    connection.close()


def remove_user():
    """Remove user from database"""
    # Print current users
    view_users()
    # Connect to sqlite3 db
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    # Prompt for username and password 
    username = input("Userid to remove from db: ").strip()
    # Check user does not exist
    cursor.execute('''DELETE FROM users WHERE userid=?''', (username,))
    connection.commit()
    connection.close()



if __name__=="__main__":
    # Check db exists or create new db
    # and add users(userid,pwd) table
    connection=None
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor=connection.cursor()
        sql="""CREATE TABLE IF NOT EXISTS users(
                userid TEXT,
                pwd TEXT);"""
        cursor.execute(sql)
        connection.commit()
        connection.close()
    except Error:
        print(Error)


    modifying=True
    while modifying:
        msg = ("\nWould you like to add/remove/view users?\n"
               "--> Type a/r/v, or q to quit: ")
        choice = input(msg)
        if choice.lower().strip()=="a":
            add_user()
        elif choice.lower().strip()=="r":
            remove_user()
        elif choice.lower().strip()=="v":
            view_users()
        elif choice.lower().strip()=="q":
            exit(0)



# From command line open db as 'sqlite3 name.db';
# view tables with '.tables' and view content with
# 'SELECT * FROM tablename'.
#
# Columns in "users" table: userid, pwd

