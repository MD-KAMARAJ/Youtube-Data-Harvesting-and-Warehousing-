# Youtube Data Harvesting and Warehousing
## Overview
This project aims to harvest data from YouTube channels using the YouTube API and store it in MYSQL database. 
The harvested data includes channel information, video data, and comment data it is stored in MYSQL, you can access it and do further analysis.

## Features
Import YouTube channel data using the Google API and Exporting it to MYSQL.
Clean and structure the imported data.
Export the cleaned data to MySQL for further analysis.
View and query the data in the Streamlit app.

## Build with
- pymysql
- pandas
- googleapiclient.discovery
- datetime
- isodate
- streamlit
- streamlit_option_menu
- time
- base64
- plotly

## Settingup Instructions
- Clone the repository to your local machine using `` .
- Install Python (if not already installed).
- Install the required libraries.
- Obtain a Google API key for the YouTube API from the Google Developers Console.
- Ensure MySQL is installed and running on your machine.

## Running the Application
- Open a terminal and navigate to the project directory.
- Run the application using the command `streamlit run main.py`.
- Access the Streamlit app in your web browser by opening the link displayed in the terminal (usually http://localhost:8501).

## Exporting Data to MYSQL
- Enter the YouTube channel ID and API key in the Streamlit tab1 and tab2.
- Click the "Fetch and Save" button to import the data from the specified YouTube channel to python.
- Specify the MySQL database connection details (host, port, database name, username, password).
- The exported data includes channel data, video data, and comment data.

## Viewing and Querying Data
- The ""Channel list" selection box displays the list of Extracted youtube channel where user can select a channel and saved its data to MySQL.
- Use the "10 SQL Queries" tab to view the selected queries.

## Author

**KAMARAJ M.D** - *Initial work* - MD-KAMARAJ

## License

------------------------
