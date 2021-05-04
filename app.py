import dash
import dash_html_components as html
import dash_core_components as dcc
import dash_table
import os
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import warnings
from greedy_single import GreedyHeuristic
import webbrowser


# Ignore warnings
warnings.filterwarnings('ignore')


# Function used
def scale_dots(input_df):

  max_val = max(input_df['value'])
  min_val = min(input_df['value'])
  size_min = 10
  size_max = 30

  if len(input_df) == 1:
    new_sizes = [size_min]

  else:
    if max_val == min_val:
      new_sizes = [size_min for i in range(len(input_df))]

    else:
      new_sizes = list((size_max * (input_df['value'] - min_val) + size_min * (max_val - input_df['value'])) / (max_val - min_val))

  return new_sizes


# -------------------------------
# Get data path
# -------------------------------
cwd = os.getcwd()
print(cwd)
data_PATH = '%s/data/' % cwd

app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])
map_default_style = 'open-street-map'

# -------------------------------
# Load data
# -------------------------------

# location information
file_staging = 'df_staging.csv'
df_staging = pd.read_csv(data_PATH + file_staging)
dict_staging_lat = dict(zip(df_staging['code'], df_staging['latitude']))
dict_staging_lon = dict(zip(df_staging['code'], df_staging['longitude']))
dict_staging_type = dict(zip(df_staging['code'], df_staging['type']))

cols = ['code', 'latitude', 'longitude']
df_staging = df_staging[cols]
df_staging.set_index('code', drop=True, inplace=True)
dict_staging = df_staging.to_dict(orient='index')

# location information
file_sender = 'df_sender.csv'
df_sender = pd.read_csv(data_PATH + file_sender)
dict_sender_lat = dict(zip(df_sender['code'], df_sender['latitude']))
dict_sender_lon = dict(zip(df_sender['code'], df_sender['longitude']))
dict_sender_type = dict(zip(df_sender['code'], df_sender['type']))

# location information
file_receiver = 'df_receiver.csv'
df_receiver = pd.read_csv(data_PATH + file_receiver)
dict_receiver_lat = dict(zip(df_receiver['code'], df_receiver['latitude']))
dict_receiver_lon = dict(zip(df_receiver['code'], df_receiver['longitude']))
dict_receiver_type = dict(zip(df_receiver['code'], df_receiver['type']))

# code names
file_original = 'healthcare_facilities.csv'
df_loc_original = pd.read_csv(data_PATH + file_original)
dict_name = dict(zip(df_loc_original['NID'], df_loc_original['NAME']))
df_receiver['name'] = df_receiver['nid'].map(dict_name)
df_sender['name'] = df_receiver['nid'].map(dict_name)

dict_sender_id_name = dict(zip(df_sender['code'], df_sender['name']))
dict_receiver_id_name = dict(zip(df_receiver['code'], df_receiver['name']))

# ----------------------------------------------------
# App layout
app.layout = html.Div(
    id="app-container",
    children=[
        # Hidden div to store intermediate data
        dcc.Store(id='intermediate-value'),
        # ---------------------
        # Banner
        # ---------------------
        html.Div(
            id="banner",
            className="row",
            children=[html.H1("Patient Evacuation Dashboard", style={'text-align': 'center'})],
        ),

        # ---------------------
        # ROW 1
        # ---------------------
        # row divider
        html.Div(
            html.Hr()
        ),

        html.Div(
            children=[
                dcc.Markdown('''***Add inputs to heuristic***'''),
                html.Div(className='row')
            ]
        ),


        # column 1
        html.Div(
            id='input-column-1',
            className='two columns',
            children=[
                dcc.Markdown('''**Choose Staging Areas**'''),
                dcc.Checklist(id='staging_area_location',
                              options=[
                                  {'label': 'a1', 'value': 'a1'},
                                  {'label': 'a2', 'value': 'a2'},
                                  {'label': 'a3', 'value': 'a3'},
                                  {'label': 'a4', 'value': 'a4'},
                                  {'label': 'a5', 'value': 'a5'}
                              ],
                              value=['a1']
                              )
            ]
        ),

        # column 2
        html.Div(
            id='input-column-2',
            className='three columns',
            children=[
                dcc.Markdown('''**Choose Number of Staging Areas**'''),
                dcc.RadioItems(id='num_staging_areas',
                               options=[
                                  {'label': '1', 'value': 1},
                                  {'label': '2', 'value': 2},
                                  {'label': '3', 'value': 3},
                                  {'label': '4', 'value': 4},
                                  {'label': '5', 'value': 5}
                               ],
                               value=1
                               )
            ]
        ),

        # column 3
        html.Div(
            id='input-column-3',
            className='three columns',
            children=[
                dcc.Markdown('''**Choose Routing Strategy**'''),
                dcc.RadioItems(id='routing_strategy',
                               options=[
                                  {'label': 'Restrictive', 'value': 1},
                                  {'label': 'Relaxed', 'value': 2}
                               ],
                               value=1
                               )
            ]
        ),

        # column 4
        html.Div(
            id='input-column-4',
            className='three columns',
            children=[
                html.Button('Run', id='start-heuristic', n_clicks=0),
                # dcc.Div(id='progress-value',),
                # html.Br(),
                dcc.Loading(id="loading",
                            children=[
                                html.Div(id="loading-output-2")
                            ],
                            type="default",
                            ),
                html.Div(id='click_status', children=[]),
            ]
        ),

        # right column
        # html.Div(
        #     id='heuristic-right-column',
        #     className='seven columns',
        #     children=[
        #         html.Div(id='heuristic-output', children='Click the Run button'),
        #         dash_table.DataTable(id='heuristic-output-table',
        #                              columns=[{'name': i, 'id': i} for i in ['staging', 'sender', 'receiver', 'staging1', 'vehicleType', 'patientType', 'scenario', 'value']],  # receiver / name
        #                              page_current=0,
        #                              page_size=10,
        #                              page_action='custom')
        #     ]
        # ),

        # ---------------------
        # ROW 2
        # ---------------------
        # row divider
        html.Div(
            className='row'
        ),
        html.Hr(),

        # left column
        html.Div(
            id='left-column',
            className='one columns',
            children=[
                html.Br(),
                html.Br(),
                dcc.Markdown('''**Scenarios**'''),
                dcc.Slider(id='scenario_slider',
                           min=1,
                           max=25,
                           step=1,
                           marks={i + 1: 's{}'.format(i + 1) for i in range(25)},
                           value=1,
                           vertical=True,
                           verticalHeight=400
                           )
            ]
        ),

        # middle column
        html.Div(
            id='middle-column',
            className='two columns',
            children=[
                html.Br(),
                html.Br(),
                dcc.Markdown('''**Evacuating Locations**'''),
                dcc.Checklist(id='location_type',
                              options=[{'label': 'Hospital', 'value': 'HOSPITAL'},
                                       {'label': 'Nursing home', 'value': 'NH'}],
                              value=[]
                              ),
                html.Br(),
                dcc.Checklist(id='patient_type',
                              options=[{'label': 'Critical', 'value': 'c'},
                                       {'label': 'Non-critical', 'value': 'n'}],
                              value=[]
                              ),
                html.Hr(),
                html.Div(id='output_container_1', children=[]),

                html.Hr(),
                dcc.Dropdown(id='sender-list', value='initial')
            ]
        ),

        # right column
        html.Div(
            id='right-column',
            className='eight columns',
            children=[
                dcc.Graph(id='my_sender_map', figure={})
            ]
        ),
        # ---------------------
        # ROW 3
        # ---------------------
        # row divider
        html.Div(
            className='row'
        ),
        html.Hr(),

        # left column
        html.Div(
            id='middle-left-column',
            className='five columns',
            children=[
                html.Br(),
                html.Br(),
                dcc.Markdown(id='output_container_2', children=[]),
                html.H6(id='evac_map_header', style={'text-align': 'left'}),
                dash_table.DataTable(id='receiver-list_table',
                                     columns=[{'name': i, 'id': i} for i in ['name', 'value']],  # receiver / name
                                     page_current=0,
                                     page_size=10,
                                     page_action='custom')
            ]
        ),

        # right column
        html.Div(
            id='middle-right-column',
            className='six columns',
            children=[
                dcc.Graph(id='indv_sender_map', figure={})
            ]
        )
    ]
)

# ------------------------------------------------------------------------------
# Connect the Plotly graphs with Dash Components
@ app.callback(
    Output(component_id='intermediate-value', component_property='data'),
    Output(component_id='loading-output-2', component_property='children'),
    Output(component_id='click_status', component_property='children'),
    Input(component_id='start-heuristic', component_property='n_clicks'),
    state=[State(component_id='staging_area_location', component_property='value'),
           State(component_id='num_staging_areas', component_property='value'),
           State(component_id='routing_strategy', component_property='value')]
)
def run_heuristic(click_count, list_input_stg_area, int_num_stg_area, int_routing_strategy):

  # Don't run unless the button has been pressed
  if not click_count:
    raise PreventUpdate

  c = GreedyHeuristic()

  # case file location
  # path = '/Users/kyoung/Box Sync/github/dash/pelo/data/'
  # directory = 'case1'

  path = '/Users/kyoung/Box Sync/github/pelo_run/'
  directory = 'test_100_senders_v2_Iter[1]_Trip[double]_Opt[1]_AmbusCR[0]_Sender[all]_AmbusMin[20]_shelter[0]_g[1]'

  # inputs to the heuristic
  list_stg_areas = list_input_stg_area
  routing_strategy = int_routing_strategy
  sort_column_type = 'weight1'
  input_staging_areas = int_num_stg_area

  # Run model
  heuristic_output = c.get_solution(path, directory, list_stg_areas, routing_strategy, sort_column_type, input_staging_areas)

  vehicle_locations = heuristic_output[0]
  obj_value = "{:,}".format(int(heuristic_output[2]))

  output_string = "%s,  %s,  %s" % (vehicle_locations, click_count, obj_value)

  df_solution = heuristic_output[1]

  return df_solution.to_json(date_format='iso', orient='split'), output_string, click_count


@ app.callback(
    [Output(component_id='my_sender_map', component_property='figure'),
     Output(component_id='sender-list', component_property='options'),
     Output(component_id='output_container_1', component_property='children')],
    [Input(component_id='scenario_slider', component_property='value'),
     Input(component_id='location_type', component_property='value'),
     Input(component_id='patient_type', component_property='value'),
     Input(component_id='intermediate-value', component_property='data')]
)
def update_sender_map(scenario_name, loc_types, patient_types, df_result_json):

  # Define a default map setting
  center_lat = 29.5
  center_lon = -95
  map_size = 600
  mark_size_max = 20
  default_zoom = 7
  color_map = {"HOSPITAL": "blue", "NH": "green", "STG": 'orange'}

  try:
    df_result = pd.read_json(df_result_json, orient='split')
  except ValueError:
    container = "Run heuristic"
    plot = [center_lat, center_lon]
    plot = pd.DataFrame(plot).T
    plot.columns = ['latitude', 'longitude']
    fig = px.scatter_mapbox(plot,
                            lat="latitude",
                            lon="longitude",
                            size_max=mark_size_max,
                            opacity=0,
                            zoom=default_zoom,
                            height=map_size,
                            mapbox_style=map_default_style)  # carto-positron)

    list_senders = []
    dropdown_list = [{'label': i, 'value': i} for i in list_senders]

    return fig, dropdown_list, container

  # If heuristic has been run
  list_staging_areas = list(df_result['staging'].unique())

  dff = df_result.groupby(['scenario', 'sender', 'patientType'])[['value']].sum()
  dff.reset_index(inplace=True)

  if scenario_name <= 9:
    input_scenario = 'n0%s' % scenario_name
  else:
    input_scenario = 'n%s' % scenario_name

  dff['type'] = dff['sender'].map(dict_sender_type)
  dff['latitude'] = dff['sender'].map(dict_sender_lat)
  dff['longitude'] = dff['sender'].map(dict_sender_lon)

  dff = dff[dff['scenario'] == input_scenario]
  dff = dff[dff['type'].isin(loc_types)]
  dff = dff[dff['patientType'].isin(patient_types)]
  print(dff)

  list_senders = list(dff['sender'].unique())
  dropdown_list = [{'label': i, 'value': i} for i in list_senders]

  if len(dff) == 0:
    container = "No location found"
    plot = [center_lat, center_lon]
    plot = pd.DataFrame(plot).T
    plot.columns = ['latitude', 'longitude']
    fig = px.scatter_mapbox(plot,
                            lat="latitude",
                            lon="longitude",
                            size_max=mark_size_max,
                            opacity=0,
                            zoom=default_zoom,
                            height=map_size,
                            mapbox_style=map_default_style)  # carto-positron)

  else:

    fig = go.Figure()

    # Add sending locations on the map
    list_location_types = list(dff['type'].unique())
    for input_location_type in list_location_types:
      dfff = dff[dff['type'] == input_location_type]
      new_sizes = scale_dots(dfff)
      hover_text = [dict_sender_id_name[i] for i in dfff['sender']]

      fig.add_trace(go.Scattermapbox(name=input_location_type,
                                     lat=dfff['latitude'],
                                     lon=dfff['longitude'],
                                     mode='markers',
                                     marker=go.scattermapbox.Marker(
                                         size=new_sizes,
                                         color=color_map[input_location_type]),
                                     hoverinfo='text',
                                     text=hover_text)
                    )

    location_type = "STG"
    stg_lats = [dict_staging[i]['latitude'] for i in list_staging_areas]
    stg_lons = [dict_staging[i]['longitude'] for i in list_staging_areas]

    # Add staging areas on the map
    fig.add_trace(go.Scattermapbox(name=location_type,
                                   lat=stg_lats,
                                   lon=stg_lons,
                                   mode='markers',
                                   marker=go.scattermapbox.Marker(
                                       size=20,
                                       color=color_map[location_type]),
                                   hoverinfo='text',
                                   text=list_staging_areas
                                   )
                  )

    fig.update_layout(
        showlegend=True,
        mapbox={
            'center': {'lat': center_lat, 'lon': center_lon},
            'zoom': default_zoom,
            'style': map_default_style
        }
    )

    container = "Locations found: %s" % len(list_senders)

  # mapbox_token = 'pk.eyJ1IjoiZXJpY2tpbTkyNiIsImEiOiJja2tlemxjczgwNGI2MnJvaGo0NnAwNmprIn0.dNFlMqQMoGEAgebt5kbz_w'
  # px.set_mapbox_access_token(open(mapbox_token).read())

  return fig, dropdown_list, container


@ app.callback(
    [Output(component_id='indv_sender_map', component_property='figure'),
     Output(component_id='output_container_2', component_property='children'),
     Output(component_id='receiver-list_table', component_property='data')],
    [Input(component_id='scenario_slider', component_property='value'),
     Input(component_id='sender-list', component_property='value'),
     Input(component_id='receiver-list_table', component_property='page_current'),
     Input(component_id='receiver-list_table', component_property='page_size'),
     Input(component_id='intermediate-value', component_property='data')]
)
def update_receiver_map(scenario_name, sender_name, page_current, page_size, df_result_json):

  center_lat = 29.5
  center_lon = -95
  map_size = 600
  mark_size_max = 20
  default_zoom = 7

  try:
    dff = pd.read_json(df_result_json, orient='split')
  except ValueError:
    container = '**%s**' % ("Run Heuristic")
    plot = [center_lat, center_lon]
    plot = pd.DataFrame(plot).T
    plot.columns = ['latitude', 'longitude']
    fig = px.scatter_mapbox(plot,
                            lat="latitude",
                            lon="longitude",
                            size_max=mark_size_max,
                            opacity=0,
                            zoom=default_zoom,
                            height=map_size,
                            mapbox_style=map_default_style)  # carto-positron)

    d = {'name': ['N/A'], 'value': ['N/A']}
    dfff = pd.DataFrame(data=d)
    dfff = dfff.to_dict('records')
    return fig, container, dfff

  # If result has been found
  if scenario_name <= 9:
    input_scenario = 'n0%s' % scenario_name
  else:
    input_scenario = 'n%s' % scenario_name

  # second input
  dict_sender_id_name['initial'] = 'Choose a sender'  # default display with no location chosen
  container = '**Evacuating Location: %s (%s)**' % (dict_sender_id_name[sender_name], input_scenario)

  dff = dff.loc[dff['sender'] == sender_name]
  dff = dff.loc[dff['scenario'] == input_scenario]
  dff = dff.groupby(['receiver'])[['value']].sum()
  dff.reset_index(inplace=True)

  # Add names to facility location
  dfff = dff.iloc[page_current * page_size:(page_current + 1) * page_size]
  dfff['name'] = dfff['receiver'].map(dict_receiver_id_name)
  dfff = dfff[['name', 'value']]
  dfff = dfff.to_dict('records')
  # dfff = dff.iloc[page_current * page_size:(page_current + 1) * page_size].to_dict('records')

  dff['latitude'] = dff['receiver'].map(dict_receiver_lat)
  dff['longitude'] = dff['receiver'].map(dict_receiver_lon)
  dff['type'] = dff['receiver'].map(dict_receiver_type)

  color_map = {"HOSPITAL": "blue", "NH": "green"}

  if len(dff) == 0:
    plot = [center_lat, center_lon]
    plot = pd.DataFrame(plot).T
    plot.columns = ['latitude', 'longitude']
    fig = px.scatter_mapbox(plot,
                            lat="latitude",
                            lon="longitude",
                            size_max=mark_size_max,
                            opacity=0,
                            zoom=default_zoom,
                            height=map_size,
                            mapbox_style=map_default_style)  # carto-positron)

  else:
    center_lon = dict_sender_lon[sender_name]
    center_lat = dict_sender_lat[sender_name]
    default_zoom = 8

    fig = go.Figure()

    new_sizes = scale_dots(dff)

    fig.add_trace(go.Scattermapbox(name='Receiver',
                                   lat=dff['latitude'],
                                   lon=dff['longitude'],
                                   mode='markers',
                                   marker=go.scattermapbox.Marker(
                                        size=new_sizes,
                                        color=[color_map[i] for i in dff['type']]),
                                   hoverinfo='text',
                                   text=dff['receiver'],
                                   )
                  )

    fig.add_trace(go.Scattermapbox(name='Sender',
                                   lat=[center_lat],
                                   lon=[center_lon],
                                   mode='markers',
                                   marker=go.scattermapbox.Marker(
                                       size=20,
                                       color='red'),
                                   hoverinfo='text',
                                   text=sender_name
                                   )
                  )

    fig.update_layout(
        showlegend=True,
        mapbox={
            'center': {'lat': center_lat, 'lon': center_lon},
            'zoom': default_zoom + 2,
            'style': map_default_style
        }
    )

  return fig, container, dfff


def open_browser(port_number):
  browser_path = 'open -a /Applications/Safari.app %s'
  url = "http://localhost:%s/" % port_number

  if not os.environ.get("WERKZEUG_RUN_MAIN"):
    webbrowser.get(browser_path).open_new(url)

  app.run_server(debug=True, port=port_number)


# ----------------------------------------------------
if __name__ == "__main__":
  port_number = 9000
  open_browser(port_number)
