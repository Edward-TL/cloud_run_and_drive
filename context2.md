In main.py consider that there are two scenarios:
1. The file does not exist, so it will be created.
2. The file exists, so it will be updated.

A way to check if the file exists is by file_manager.json. If there the PARQUET_FILE_ID is empty, it means that the file does not exist.

In both cases, the file will be updated with the data received from the Wix API.

The data at the file will alway be sorted, due to the update will be done through an append method, using pd.concat([df, df_new], ignore_index=True).

In case the file exists, the function will check if the data received from the Wix API is different from the data already in the file using the transaction_id or timestamp, due to there can only be one transaction with that puntual period of time. Consider this as the best way to check the last update is calling the last value of the transaction_id or timestamp and check if new data's timestamp is greater than the last value of the timestamp. If it is not, it means that the data is already in the file and it will not be updated.

The process could be traduced as:
1. Check if the file exists by checking if the PARQUET_FILE_ID is empty.
2.a If the file exists: 
    2.a.1 Download the parquet file with GoogleDrive class and pass it directly to pd.read_parquet().
    2.a.2 Check if the data received from the Wix API is different from the data already in the DataFrame using the transaction_id or timestamp.
    2.a.3 Set updated_df as True if the data is different, False otherwise.
2.b If the file does not exist:
    2.b.1 Create an empty pandas DataFrame using df = pd.DataFrame().
    2.b.2 Set updated_df as True.

3. If updated_df is True, update the df with the new data using pd.concat([df, df_new], ignore_index=True).
4. If updated_df is True, update the parquet file with the new data using df.to_parquet(f"{FILE_NAME}.parquet") and sending it to GoogleDrive using GoogleDrive class.
5. If updated_df is True, update the excel file with the new data using df.to_excel(f"{FILE_NAME}.xlsx") and sending it to GoogleDrive using GoogleDrive class.
6. Update the file_manager.json with the new PARQUET_FILE_ID and EXCEL_FILE_ID.

