import os
import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import plotly.graph_objects as go
# import plotly.figure_factory as ff
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from plotly.tools import mpl_to_plotly
import seaborn as sns
sns.set()

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# base data loading
b_epnt = 'https://data.cityofnewyork.us/resource/uvpi-gqnh.json?'
tree_q = b_epnt + '$select=distinct spc_common'.replace(' ', '%20')
boro_q = b_epnt + '$select=distinct boroname'.replace(' ', '%20')
df = pd.read_json(tree_q.replace(' ', '%20'))
tree_names = pd.read_json(tree_q.replace(' ', '%20')).values.flatten()
tree_names = tree_names[~pd.isna(tree_names)].tolist()
boro_names = pd.read_json(boro_q.replace(' ', '%20')).values.flatten()
boro_names = boro_names[~pd.isna(boro_names)].tolist()


app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

server = app.server

app.layout = html.Div([
    html.H3('Select a species and borough to search'),
    
    ## selection divs + button
    # spc_common
    html.Div([
        dcc.Dropdown(
            id='spc_common',         
            options=[{'label':i, 'value': i} for i in tree_names],
            # multi=True,
            value=tree_names[0],
            style={'width': '220px'}),
        html.Div(id='spc_common_sel')
    ], style={'float':'left'}),
    
    # boro
    html.Div([
        dcc.Dropdown(
            id='boro',         
            options=[{'label':i, 'value': i} for i in boro_names],
            # multi=True,
            value=boro_names[0],
            style={'width': '220px'}),
        html.Div(id='boro_sel')
    ], style={'float':'right'}),
    
    # search button
    html.Button('Search', id='search_button', style={'display':'inline-block'}),
    
    # query_bar
    dcc.Graph(id='query_bar',),
    
    # stwd_bar
    dcc.Graph(id='stwd_bar',),
    
    # query_table
    html.Div(id='query_table', style={'padding': 20},), 
    
    
    
])

##### CALLBACKS #####
@app.callback(
    Output('spc_common_sel', 'children'),
    [Input('spc_common', 'value')]
)
def update_spc_common_sel(name):
    return f'Tree species selected: {name}'

@app.callback(
    Output('boro_sel', 'children'),
    [Input('boro', 'value')]
)
def update_boro_sel(name):
    return f'Borough selected: {name}'

@app.callback(
    [Output('query_table', 'children'), 
     Output('query_bar', 'figure'),
     Output('stwd_bar', 'figure')], 
    [Input('search_button', 'n_clicks')],
    [State('spc_common', 'value'),
     State('boro', 'value')]
)
def do_query(clicks, tree, boro, limit=999999):
    if not clicks:
        raise PreventUpdate
        
    # do query + get data
    q = b_epnt + f"$select=spc_common,health,steward,count(tree_id)" +\
            f"&$where=boroname=\'{boro}\'" +\
            f" AND spc_common=\'{tree}\'" +\
            f"&$group=spc_common,health, steward"
    df = pd.read_json(q.replace(' ', '%20'))

    # make overall health condition 
    hdf = df.groupby('health').sum()
    hdf['health_proportion'] = hdf['count_tree_id']/hdf['count_tree_id'].sum()
    hdf.reset_index(inplace=True)
    hdf['health'] = pd.Categorical(hdf['health'], ['Poor', 'Fair', 'Good'])
    hdf.sort_values('health', axis=0, inplace=True)
    query_bar = go.Figure()
    query_bar.add_trace(go.Bar(x = hdf['health'], y=hdf['health_proportion'],
                               text='count: ' + hdf['count_tree_id'].astype(str),
                               textposition='auto', marker = dict(color=['Red','Blue', 'Green'])))
    query_bar.update_layout(title_text = 'Health Proportions')

    # make steward bar
    df['health'] = pd.Categorical(df['health'], ['Poor', 'Fair', 'Good'])
    df.sort_values(['steward', 'health'], inplace=True)
    df['color'] = df['health'].map({'Poor': 'Red', 'Fair': 'Blue', 'Good': 'Green'})
    prop = []
    stwd_grouped = df.groupby('steward')
    for stwd, group in stwd_grouped:     
        prop.extend(group['count_tree_id']/group['count_tree_id'].sum())
    df['health_proportion'] = prop
    df['steward'] = pd.Categorical(df['steward'], ['None', '1or2', '3or4', '4orMore'])
    df.sort_values(['steward', 'health'], axis=0, inplace=True)
    stwd_bar = go.Figure()
    stwd_bar.add_trace(go.Bar(x = [df['steward'], df['health']],
                         y=df['health_proportion'],
                         text='count: ' + df['count_tree_id'].astype(str),
                         textposition='auto', marker = dict(color=df['color'])))
    stwd_bar.update_layout(title_text = 'Health Proportions by Steward')


    
    # make the table
    columns = [{'name': i, 'id': i,} for i in (df.columns)]
    query_tb = dash_table.DataTable(
        data = df.to_dict('rows'), 
        columns = columns,
        fixed_columns={'headers': True, 'data': 1},
        fixed_rows={'headers': True,'data': 0},
        style_table={
            'maxHeight': '250px', 'maxWidth': '900px',
            'overflowY': 'scroll', 'overflowX': 'scroll'},
        style_cell={'width': '150px'},
        style_data_conditional=[{
            'if': {
                'row_index': 'odd'
            },
            'backgroundColor': 'rgb(248, 248, 248)'
        }],
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold',
            'border': '1px solid blue',
        },
    )
    return query_tb, query_bar, stwd_bar


if __name__ == '__main__':
    app.run_server(debug=True)
