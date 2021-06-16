import pandas as pd
import plotly.express as px
import yfinance as yf
import streamlit as st
import plotly.graph_objects as pg_o
import base64

def get_table_download_link(df):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    in:  dataframe
    out: href string
    """
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
    href = f'<a href="data:file/csv;base64,{b64}">Download csv file</a>'
    st.markdown(href, unsafe_allow_html=True)

def import_data():
    uploaded_file = st.file_uploader('Upload here your trade history')
    if uploaded_file is not None:
        transactions = pd.read_csv(uploaded_file)
        transactions = format_date(transactions)
    else:
        st.title('Hello!')
        st.subheader('If you are new here, a quick guide below can help you use this tool')
        st.write('This tool is capable of display you the performance of your investment portfolio.')
        st.write('All you need to do is upload a .csv file at the top of this page. An example can be downloaded [here](https://drive.google.com/file/d/1GNjWrr8G3h6ubYk6OT1S4RTLCyf1uzSm/view?usp=sharing)')
        st.subheader('Guidelines')
        st.write('''Your file must constain the following columns, with their respective information:
                    \n - id = identification for your transaction. It can be set as a sequence
                    \n - purchase_date = day that you bought the stock (format "dd/mm/yyyy")
                    \n - sell_date = day that you sold the stock. If you still have it, leave it blank (format "dd/mm/yyyy")
                    \n - ticker = your stock ticker, as it in [https://finance.yahoo.com/](https://share.streamlit.io/mesmith027/streamlit_webapps/main/MC_pi/streamlit_app.py)
                    \n - purchase_price = for how much you paid each share (use "." as decimal)
                    \n - selling_price = for how much you sold each share (if you haven't sold, leave blanked. use "." as decimal)
                    \n - quantity = how many shares you bought
                    \n - lavel = if this trade is part of a cluster within your portfolio''')
        st.write('If these requeriments are fullfilled properly, you should receive a dashboard like this...')
        transactions = pd.DataFrame([[1,'12/4/2021','31/05/2021','COCA34.SA',50.3,48.2,5,'Solo']],columns = ['id','purchase_date','sell_date','ticker','purchase_price','selling_price','quantity','label'])
        transactions = format_date(transactions)

    return transactions


def format_date(transactions):
    transactions['purchase_date'] = pd.to_datetime(transactions['purchase_date'], format='%d/%m/%Y')
    transactions['sell_date'] = pd.to_datetime(transactions['sell_date'], format='%d/%m/%Y')

    return transactions


@st.cache
def build_portfolio_history(transactions):
    portfolio_history = pd.DataFrame()
    for trade in transactions.itertuples():
        stock_history = get_price_history(trade.ticker)
        sell_date = complete_unsold_stocks(trade.sell_date)
        trade_history = create_price_parameter(stock_history, trade.quantity, trade.purchase_price, trade.selling_price,
                                               trade.purchase_date, sell_date)
        trade_history = trade_history.loc[
            (trade_history['Date'] >= trade.purchase_date) & (trade_history['Date'] <= trade.sell_date), ['Date',
                                                                                                          'Close',
                                                                                                          'compare']]
        trade_history[['Code']] = trade.ticker
        trade_history['label'] = trade.label
        trade_history = create_trade_id(trade_history, portfolio_history)
        portfolio_history = pd.concat([portfolio_history, trade_history])

    return portfolio_history


def get_price_history(trade_ticker):
    stock_history = yf.Ticker(trade_ticker).history(period="max")
    return stock_history


def complete_unsold_stocks(sold_date):
    if pd.isnull(sold_date) == True:
        sell_date = pd.to_datetime('today')
    else:
        sell_date = sold_date
    return sell_date


def create_price_parameter(stock_history, trade_quantity, trade_purchase_price, trade_selling_price,
                           trade_purchase_date, sell_date):
    trade_history = stock_history[['Open', 'Close']].multiply(trade_quantity, axis="index").reset_index()
    trade_history = trade_history.reset_index()
    trade_history.loc[trade_history['index'] != 0, 'compare'] = trade_history['Close'].shift(1)
    trade_history.loc[trade_history['Date'] == trade_purchase_date, 'compare'] = trade_purchase_price * trade_quantity
    trade_history.loc[trade_history['Date'] == sell_date, 'Close'] = trade_selling_price * trade_quantity

    return trade_history


def create_trade_id(trade_history, portfolio_history):
    if not 'id' in portfolio_history.columns:
        trade_history['id'] = 1
    else:
        trade_history['id'] = portfolio_history['id'].max() + 1

    return trade_history


def filter_plot_data(portfolio_history, stocks_to_plot, plot_from_date, plot_to_date):
    stocks_to_plot = list(map(int, stocks_to_plot))

    if len(stocks_to_plot) == 0:
        plot_data = portfolio_history.loc[
            (portfolio_history['Date'] >= plot_from_date) & (portfolio_history['Date'] <= plot_to_date)]
    else:
        plot_data = portfolio_history.loc[
            (portfolio_history['Date'] >= plot_from_date) & (portfolio_history['Date'] <= plot_to_date) & (
                portfolio_history['id'].isin(stocks_to_plot))]

    if len(filter_label) != 0:
        plot_data = plot_data.loc[plot_data['label'].isin(filter_label)]

    return plot_data


def compute_y_values(plot_data):
    plot_data = plot_data[['Date', 'Close', 'compare']].groupby('Date').sum().reset_index()
    plot_data['Revenue ($)'] = (plot_data['Close'] - plot_data['compare'])
    plot_data['Cumulative Revenue ($)'] = plot_data['Revenue ($)'].cumsum()
    plot_data['Revenue (%)'] = plot_data['Revenue ($)'] / plot_data['compare']
    plot_data['Cumulative Revenue (%)'] = plot_data['Revenue (%)'].cumsum()

    return plot_data


def plot_on_dashboard(plot_data):
    build_plot_framework(plot_data, 'Cumulative Revenue (%)', 'Revenue (%)')
    build_plot_framework(plot_data, 'Cumulative Revenue ($)', 'Revenue ($)')


def build_plot_framework(plot_data, plot_title_1, plot_title_2):
    c1, c2 = st.beta_columns(2)

    with c1:
        build_line_plot(plot_data, plot_title_1)

    with c2:
        build_financial_plot(plot_data, plot_title_2)


def build_line_plot(plot_data, title):
    st.subheader(title)
    fig = px.line(plot_data, x="Date", y=title)
    if '%' in title:
        fig.update_layout(yaxis_tickformat='%')
    st.write(fig)


def build_financial_plot(plot_data, title):
    st.subheader(title)

    fig = pg_o.Figure(pg_o.Waterfall(
        orientation="v",
        x=plot_data["Date"],
        textposition="outside",
        y=plot_data[title],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
    ))
    if '%' in title:
        fig.update_layout(yaxis_tickformat='%')
    st.write(fig)


if __name__ == "__main__":
    st.set_page_config(layout='wide')


    # EXTRACT
    transactions = import_data()

    # TRANSFORM

    portfolio_history = build_portfolio_history(transactions)
    freezed_transactions = transactions.copy()

    stocks_to_plot = st.sidebar.multiselect('Which trades are going to be analysed?',
                                            freezed_transactions['id'].astype('str').unique())
    filter_label = st.sidebar.multiselect('Which cluster is going to be analysed?',
                                          freezed_transactions['label'].unique())
    plot_from_date = st.sidebar.date_input('Select start of series',
                                           value=pd.to_datetime('today') + pd.offsets.Day(-90))
    plot_from_date = pd.to_datetime(plot_from_date)
    plot_to_date = st.sidebar.date_input('Select end of series')
    plot_to_date = pd.to_datetime(plot_to_date)

    st.title('Summary')
    st.header('Transactions')
    st.write(freezed_transactions)

    st.header('Graphs')
    plot_data = filter_plot_data(portfolio_history, stocks_to_plot, plot_from_date, plot_to_date)
    plot_data = compute_y_values(plot_data)
    plot_on_dashboard(plot_data)

    # LOAD


