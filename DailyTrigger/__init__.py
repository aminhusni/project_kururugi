import datetime
import logging
import os
import pytz

import azure.functions as func
from azure.storage.blob import BlobServiceClient, BlobClient, ContentSettings

import pandas as pd
import plotly.express as px

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)

    timeZ_My = pytz.timezone('Asia/Kuala_Lumpur')
    now = datetime.datetime.now(timeZ_My)
    current_time = now.strftime("%d/%m/%Y %H:%M:%S")

    # Get datapoints from official CITF Malaysia and process as CSV with Pandas
    url = "https://raw.githubusercontent.com/CITF-Malaysia/citf-public/main/vaccination/vax_malaysia.csv"
    df = pd.read_csv(url)

    # Plot the graph
    vaccination_rate = px.line(df, x = 'date', y = 'total_daily',  
                                labels={
                                    "date": "",
                                    "total_daily": "Daily doses"
                                },
                                title='Daily Vaccination Rate (Doses)')
    vaccinated_total = px.line(df, x = 'date', y = 'total_cumul',
                                labels={
                                    "date": "",
                                    "total_cumul": "Daily doses"
                                },
                                title='Total Vaccination Dose')

    # Convert plotted graph into HTML div
    daily_rate_plot = vaccination_rate.to_html(full_html=False)
    daily_rate_plot2 = vaccinated_total.to_html(full_html=False)

    # Generate day name based on date
    df['date'] = pd.to_datetime(df['date'])
    df['day_of_week'] = df['date'].dt.day_name()

    # Plot the graph
    day_trend = px.bar(df, x='day_of_week', y='total_daily', 
                        category_orders={'day_of_week': ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]},
                        labels={
                            "day_of_week": "",
                            "total_daily": "Total doses administered to date"
                        },
                        title='Doses administed by day distribution')

    # Convert plotted graph into HTML div
    day_trend_plot = day_trend.to_html(full_html=False)

    # Get datapoints for per state in Malaysia
    url = "https://raw.githubusercontent.com/CITF-Malaysia/citf-public/main/vaccination/vax_state.csv"
    df = pd.read_csv(url)
    df_trim = df.iloc[-16:]
    df_trim = df_trim.sort_values('total_cumul')

    state_progress = px.bar(df_trim, x="total_cumul", y="state", 
                            labels={
                                "total_cumul": "Doses",
                                "state": "State",
                            },
                            title='Doses administed by state',

                            orientation='h')
    state_plot = state_progress.to_html(full_html=False)

    # Crude HTML templates
    HeadTemplate = '<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>*{box-sizing: border-box;}.header{padding: 15px;}.row::after{content: ""; clear: both; display: table;}[class*="col-"]{float: left; padding: 15px; border: 1px solid rgba(9, 255, 0, 0.733);}.col-1{width: 50%;}</style></head><body><div class="header">'
    Close = '</div>'
    RowOpen = '<div class="row">'
    ColOpen = '<div class="col-1">'
    FootClose = '</body></html>'

    # Generate the static HTML page
    with open("/tmp/index.html", "w") as f:
        f.write(HeadTemplate)
        f.write("<h1>Vaccination Statistics Malaysia</h1>")
        f.write("<a href='https://kururugi.blob.core.windows.net/kururugi/about.html'>Technical details & about</a><br>Coded by: Amin Husni (aminhusni@gmail.com)<br><br>")
        f.write("Data refreshed: " + current_time + " (MYT)")
        f.write(Close)

        f.write(RowOpen)
        f.write(ColOpen)
        f.write(daily_rate_plot)
        f.write(Close)

        #f.write("<h2>Malaysian population: 32,764,602 people<br>Target vaccination (80%): 26,211,682</h2>")
        
        f.write(ColOpen)
        f.write(daily_rate_plot2)
        f.write(Close)
        f.write(Close)

        f.write(RowOpen)
        f.write(ColOpen)
        f.write(day_trend_plot)
        f.write(Close)
        f.write(ColOpen)
        f.write(state_plot)
        f.write(Close)
        f.write(Close)

        f.write(RowOpen)
        f.write("<br>Licenses: Official datapoint: <a href='https://www.data.gov.my/p/pekeliling-data-terbuka'>Pekeliling Pelaksanaan Data Terbuka Bil.1/2015 (Appendix B)</a>")
        f.write(Close)

    connect_str = # REDACTED
    container = # REDACTED

    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    blob_client = blob_service_client.get_blob_client(container=container, blob="index.html")
    my_content_settings = ContentSettings(content_type='text/html')
    with open("/tmp/index.html", "rb") as data:
        blob_client.upload_blob(data, overwrite=True, content_settings=my_content_settings)

