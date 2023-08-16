import robin_stocks.robinhood as r  # abbreviated version of robinhoood commands
import pyotp  # authenticator


def user_login():
    # login access
    username = ''  # enter username
    password = ''  # enter password
    # AUTHENTICATOR FROM ROBINHOOD
    totp = input("Please type in your authenticator code: ")
    print("Current OTP:", totp)
    login = r.login(username, password, mfa_code=totp)
