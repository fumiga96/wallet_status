import pandas as pd
import plotly.express as px
import yfinance as yf
import streamlit as st

# functions
def get_data( path ,engine):
    df = pd.read_csv( path, engine = engine)

    return df
# resgata o historico de preco de uma companhia
def price_history(company_ticker):
    df1 = yf.Ticker(company_ticker)
    df1 = df1.history(period="max")
    return df1


# ajusta a acao de acordo com o que foi negociado na carteira
def my_wallet(company_ticker, df1, qty, date_start, date_finish, sell, buy):
    # quantidade de acoes
    df1 = df1[['Open', 'Close']].multiply(qty, axis="index").reset_index()
    # tagear as linhas relacionadas a essa acao
    df1[['Code']] = company_ticker
    # periodo de posse

    if pd.isnull(date_finish) == True:
        date_finish = pd.Timestamp("today").strftime("%m/%d/%Y")

    df1 = df1.reset_index()
    df1.loc[df1['index'] != 0, 'compare'] = df1['Close'].shift(1)
    df1.loc[df1['Date'] == date_start, 'compare'] = buy * qty
    df1.loc[df1['Date'] == date_finish, 'Close'] = sell * qty
    df1 = df1.loc[(df1['Date'] >= date_start) & (df1['Date'] <= date_finish), ['Date', 'Close', 'compare', 'Code']]

    return df1



def add_stock(df, company_ticker, date_start, date_finish, qty, sell, buy, label):
    # adquirir dados
    df1 = price_history(company_ticker)

    # ajustar as acoes de acordo com sua carteira
    df1 = my_wallet(company_ticker, df1, qty, date_start, date_finish, sell, buy)

    # concatenar dados e agrupalos pela data
    if len(df) == 0:
        df1['id'] = 1
    else:
        df1['id'] = df['id'].max() + 1

    df1['label'] = label
    df = pd.concat([df, df1])

    return df


@st.cache
def add_wallet_loop(df1):
    df = pd.DataFrame()
    for row in df1.itertuples():
        df = add_stock(df, row.ticker, row.purchase_date, row.sell_date, row.quantity, row.selling_price,
                       row.purchase_price, row.label)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    return df

def import_data():
    upload_file = st.file_uploader('Would you like to upload a set history')

    if upload_file is not None:
        df1_orig = get_data(upload_file, 'python')
        df1_orig['purchase_date'] = pd.to_datetime(df1_orig['purchase_date'], format='%d/%m/%Y')
        df1_orig['sell_date'] = pd.to_datetime(df1_orig['sell_date'], format='%d/%m/%Y')


    else:
        df1_orig = pd.DataFrame([[1, '2021-04-12', '2021-05-31', 'COCA34.SA', 50.30, 48.20, 5, 'SOLO']],columns= ['id','purchase_date', 'sell_date', 'ticker', 'purchase_price', 'selling_price', 'quantity', 'label'])

    return df1_orig


def filter(filter_stocks, filter_date_start, filter_date_end):
    filter_stocks = list(map(int, filter_stocks))

    if len(filter_stocks) == 0:
        graph = df.loc[(df['Date'] >= filter_date_start) & (df['Date'] <= filter_date_end)]
    else:
        graph = df.loc[
            (df['Date'] >= filter_date_start) & (df['Date'] <= filter_date_end) & (df['id'].isin(filter_stocks))]

    if len(filter_label) != 0:
        graph = graph.loc[graph['label'].isin(filter_label)]

    return graph


def graphs(graph):
    st.title('Growth (%)')

    c1, c2 = st.beta_columns(2)

    with c1:
        st.header('Cumulative wallet variation')
        graph1 = graph[['Date', 'Close', 'compare']].groupby('Date').sum().reset_index()
        graph1['Gains'] = graph1['Close'] - graph1['compare']
        graph1['Gains'] = graph1['Gains'] / graph1['compare']
        graph1['Gains'] = graph1['Gains'].cumsum()
        fig = px.line(graph1, x="Date", y="Gains")
        fig.update_layout(yaxis_tickformat='%')
        st.write(fig)

    with c2:
        st.header('Daily wallet variation')
        graph2 = graph[['Date', 'Close', 'compare']].groupby('Date').sum().reset_index()
        graph2['Gains'] = graph2['Close'] - graph2['compare']
        graph2['Gains'] = graph2['Gains'] / graph2['compare']
        fig2 = px.line(graph2, x="Date", y="Gains")
        fig2.update_layout(yaxis_tickformat='%')

        st.write(fig2)

    st.title('Growth ($)')

    c1, c2 = st.beta_columns(2)

    with c1:
        st.header('Cumulative wallet variation')
        graph1 = graph[['Date', 'Close', 'compare']].groupby('Date').sum().reset_index()
        graph1['Gains ($)'] = graph1['Close'] - graph1['compare']
        graph1['Gains ($)'] = graph1['Gains ($)'].cumsum()
        fig = px.line(graph1, x="Date", y="Gains ($)")
        st.write(fig)

    with c2:
        st.header('Daily wallet variation')
        graph2 = graph[['Date', 'Close', 'compare']].groupby('Date').sum().reset_index()
        graph2['Gains ($)'] = graph2['Close'] - graph2['compare']
        fig2 = px.line(graph2, x="Date", y="Gains ($)")

        st.write(fig2)

if __name__ == "__main__":

    st.write('test')
    st.set_page_config(layout = 'wide')

    #EXTRACT
    df1_orig = import_data()

    #TRANSFORM

    df = add_wallet_loop(df1_orig)
    df1 = df1_orig.copy()

    #LOAD
    st.title('Summary')
    st.write(df1)

    filter_stocks = st.multiselect('Which trades are going to be analysed?', df['id'].astype('str').unique())
    filter_label = st.multiselect('Which wallet is going to be analysed?', df['label'].unique())

    c3, c4 = st.beta_columns(2)

    with c3:
        filter_date_start = st.date_input('Select start of series')

    with c4:
        filter_date_end = st.date_input('Select end of series')

    graph = filter(filter_stocks, filter_date_start, filter_date_end)
    graphs(graph)

