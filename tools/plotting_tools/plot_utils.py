import pandas as pd
import os

class PlotUtils:

    def get_csv_data(csv_file):
        """
        Opens ET data csv files and returns a sorted and filtered dataframe
        """

        dataframe = pd.read_csv(csv_file, usecols=["filename", "date", "average_value"])

        try:
            dataframe['date'] = pd.to_datetime(dataframe['date'], format='%Y%m%d')
        except: 
            print(dataframe['date'])
            return

        dataframe = dataframe[dataframe['average_value'] >= 0]
        dataframe = dataframe.sort_values(by='date')

        return dataframe   
    

    def get_model(self, csv_file):
        return os.path.splitext(os.path.basename(csv_file))[0].split('_')[0]
    
    
    def get_adjustment(self, csv_file):
        return os.path.splitext(os.path.basename(csv_file))[0].split('_')[1]
    
    
    def get_location(self, csv_file):
        return os.path.splitext(os.path.basename(csv_file))[0].split('_')[2]