import csv
import datetime as dt
import pandas as pd
from IPython.display import display

# Extract the CSV file
file_path = 'robinhood.csv'

extracted_columns = ['Activity Date', 'Instrument',
                     'Description', 'Trans Code', 'Quantity', 'Price', 'Amount']

df = pd.read_csv(file_path, usecols=extracted_columns)

print(df)
