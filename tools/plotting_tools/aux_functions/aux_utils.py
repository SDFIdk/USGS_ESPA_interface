import pandas as pd
import sys

class AuxUtils:

    def resample_dataframe(df, resample_time):
        """
        Resamples the given DataFrame to the specified time interval and reinserts an 'id' column.

        Parameters:
        - df (pd.DataFrame): Input DataFrame with 'id', 'date', and a third column with variable names (e.g., 'cloudcover').
        - resample_time (str): Resampling period (e.g., 'W' for weekly, 'M' for monthly, or any valid resampling frequency).

        Returns:
        - pd.DataFrame: Resampled DataFrame with a new 'id' column and resampled values for the third column.
        """

        value_column = [col for col in df.columns if col not in ['id', 'date']][0]

        df_resampled = df[['date', value_column]].copy()  # Drop 'id', keep 'date' and the third column

        try:
            df_resampled = df_resampled.resample(resample_time, on='date').mean().reset_index()
        except ValueError as e:
            raise ValueError(f"Invalid resampling period: {resample_time}") from e

        df_resampled.insert(0, 'id', range(len(df_resampled)))

        return df_resampled

        
    def build_avg_cloud_dataframe(aux_data_table):
        """
        Combines data from all cloudcover data CSVs into a single average cloudcover dataframe
        """
        cloudfiles = []
        for aux_file, aux_metadata in aux_data_table.items():
            if not aux_metadata.auxtype == 'cloudcover':
                continue

            cloudfiles.append(aux_file)
            cc_metadata = aux_metadata
        return AuxUtils.average_csv_data(cloudfiles), cc_metadata
    
    
    def average_csv_data(csv_files):
        """
        Reads multiple CSV files, computes the average values for each date,
        and returns a combined DataFrame.

        Parameters:
        - csv_files (list): List of paths to CSV files

        Returns:
        - combined_df (pd.DataFrame): DataFrame containing averaged values per date
        """

        all_data = []
        for file in csv_files:

            df = pd.read_csv(file)
            df['date'] = df['date'].astype(str)
            df_grouped = df.groupby('date', as_index=False)['cloudcover'].mean()
            all_data.append(df_grouped)

        combined_df = pd.concat(all_data).groupby('date', as_index=False)['cloudcover'].mean()
        combined_df['id'] = range(1, len(combined_df) + 1)
        combined_df = combined_df[['id', 'date', 'cloudcover']]
        combined_df['date'] = pd.to_datetime(combined_df['date'], format='%Y%m%d')

        return combined_df