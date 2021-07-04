import datetime
import logging
import os
import pytz
import pathlib

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

    # Get the current generation time in MYT timezone
    timeZ_My = pytz.timezone('Asia/Kuala_Lumpur')
    now = datetime.datetime.now(timeZ_My)
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")

    # Get datapoints from official CITF Malaysia and process as CSV with Pandas
    url = "https://raw.githubusercontent.com/CITF-Malaysia/citf-public/main/vaccination/vax_malaysia.csv"
    df = pd.read_csv(url)

    last_date_data = df['date'].iloc[-1:].item()

    # Get a 7-day rolling dataset to be plotted into the vaccination_rate graph
    df['7_rolling_avg'] = df['total_daily'].rolling(7).mean()

    # Plot the graph
    # Vaccination rate daily
    vaccination_rate = px.line(df, x = 'date', y = ['total_daily', '7_rolling_avg'],
                                color_discrete_map={
                                    "total_daily": "#1f822c",
                                    "7_rolling_avg": "#FF9D3C",
                                },
                                labels={
                                    "date": "",
                                    "total_daily": "Daily doses"
                                },
                                title='Daily Vaccination Rate (Doses)')

    #vaccination_rate.update_traces(line_color='#1f822c')



    # Total vaccination dose (overall)
    vaccinated_total = px.line(df, x = 'date', y = 'total_cumul',
                                labels={
                                    "date": "",
                                    "total_cumul": "Daily doses"
                                },
                                title='Total Vaccination Dose')
    vaccinated_total.update_traces(line_color='#1f822c')

    # Calculate the amount of people vaccinated vs unvaccinated
    # Get 1 dose total to date
    single_dose_total = df['dose1_cumul'].iloc[-1:].item()
    population_total = 32764602
    # Get unvaccinated using maths lol #QuickMaths
    unvaccinated = population_total - single_dose_total

    # Put the calculations into data frame
    progress_frame = [{'type': 'Vaccinated', 'total': single_dose_total},
                    {'type': 'Unvaccinated', 'total': unvaccinated} 
                        ]
    df2 = pd.DataFrame(progress_frame)

    # Pie chart
    progress_total = px.pie(df2, title='Vaccination Progress (at least 1 dose)', values='total', names='type', color='type',
                            color_discrete_map={
                                'Vaccinated': '#3cb64c',
                                'Unvaccinated': '#29255f'
                            }
                            )

    # Get 2 dose total to date
    double_dose_total = df['dose2_cumul'].iloc[-1:].item()
    population_total = 32764602
    # Get unvaccinated using maths again #QuickMaths
    unvaccinated = population_total - double_dose_total

    # Put the calculations into data frame
    progress2_frame = [{'type': 'Vaccinated', 'total': double_dose_total},
                    {'type': 'Unvaccinated', 'total': unvaccinated} 
                        ]
    df3 = pd.DataFrame(progress2_frame)

    # Pie chart
    progress2_total = px.pie(df3, title='Vaccination Progress (2 doses)', values='total', names='type', color='type',
                            color_discrete_map={
                                'Vaccinated': '#3cb64c',
                                'Unvaccinated': '#29255f'
                            }
                            )

    # Convert plotted graph into HTML div
    daily_rate_plot = vaccination_rate.to_html(full_html=False, include_plotlyjs=False)
    daily_rate_plot2 = vaccinated_total.to_html(full_html=False, include_plotlyjs=False)
    progress_plot = progress_total.to_html(full_html=False, include_plotlyjs=False)
    progress2_plot = progress2_total.to_html(full_html=False, include_plotlyjs=False)

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
    day_trend_plot = day_trend.to_html(full_html=False, include_plotlyjs=False)

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
    state_plot = state_progress.to_html(full_html=False, include_plotlyjs=False)

    # Crude HTML templates
    HeadTemplate = open(pathlib.Path(__file__).parent / 'html_header.html', 'r').read()    
    Close = '</div>'
    RowOpen = '<div class="row">'
    ColOpen = '<div class="col-1">'
    FootClose = '</body></html>'

    # Generate the static HTML page
    with open("/tmp/index.html", "w") as f:
        f.write(HeadTemplate)
        f.write("<h1>Vaccination Statistics Malaysia</h1>")
        f.write("<a href='https://kururugi.blob.core.windows.net/kururugi/about.html'>Technical details & about</a><br>Coded by: Amin Husni (aminhusni@gmail.com)<br><br>")
        f.write("Data refreshed: " + current_time + " (MYT)<br>")
        f.write("Latest date in data: " + last_date_data + "<br>*For mobile, please use horizontal mode (rotate)<br><br>")
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
        f.write(ColOpen)
        f.write(progress_plot)
        f.write(Close)
        f.write(ColOpen)
        f.write(progress2_plot)
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

