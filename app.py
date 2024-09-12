from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
import os
import mysql.connector
import google.generativeai as genai
import plotly
import plotly.express as px
import pandas as pd
import json

# Load environment variablesdotenv
load_dotenv()

# Initialize the Flask app
app = Flask(__name__)

# Configure GenAI Key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Function to load Google Gemini Model and provide queries as response
def get_gemini_response(question, prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([prompt[0], question])
    cleaned_response = response.text.replace('```', '').replace('sql', '').strip()
    print("Cleaned SQL Query: ", cleaned_response)
    
    return cleaned_response

def generate_graph(df):
    # Automatically determine graph type based on available columns
    if 'SaleDate' in df.columns and 'TotalAmount' in df.columns:
        # If 'Date' and 'SalesAmount' exist, generate a line chart showing sales over time
        fig = px.line(df, x='SaleDate', y='TotalAmount', title='Sales Over Time')
    elif 'ProductName' in df.columns and 'Price' in df.columns:
        # If 'ProductName' and 'Quantity' exist, generate a bar chart showing sales per product
        fig = px.bar(df, x='ProductName', y='Price', title='Sales by Product')
    elif 'ProductName' in df.columns and 'TotalSales' in df.columns:
        # If 'ProductName' and 'TotalSales' exist, generate a pie chart for product sales share
        fig = px.pie(df, names='ProductName', values='TotalSales', title='Sales Share by Product')
    else:
        # Default to a scatter plot if none of the above are matched
        fig = px.scatter(df, x=df.columns[0], y=df.columns[1], title='Data Visualization')

    # Return the figure
    return fig

# Function to retrieve query from MySQL database and return columns with data
def read_sql_query(sql):
    # Connect to MySQL database
    conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB")
    )
    cur = conn.cursor()

    # Execute the SQL query
    cur.execute(sql)
    
    # Fetch the column names
    columns = [description[0] for description in cur.description]
    print(cur.description)
    
    # Fetch the data
    rows = cur.fetchall()
    
    conn.commit()
    cur.close()
    conn.close()
    
    return columns, rows

# Define your prompt
prompt = [
    """
    You are an expert in converting English questions to SQL queries for a sales database!
    The database has the following tables - Customers, Products, Sales, Sales_Items.
    
    When returning the SQL query, make sure:
    don't uyse ``` and sql word in query
    - also the sql code should not have ``` in beginning or end and sql word in output
    - For example:
      - Example 1: Total sales amount for each product.
        SQL: SELECT ProductID, SUM(Quantity * Price) FROM Sales_Items GROUP BY ProductID;
      - Example 2: List all sales transactions with customer details.
        SQL: SELECT Sales.SaleID, Sales.SaleDate, Customers.Name, Customers.Email, Sales.TotalAmount
             FROM Sales
             JOIN Customers ON Sales.CustomerID = Customers.CustomerID;

             

    """
]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_question():
    question = request.form.get('question')
    
    if question:
        try:
            # Get Gemini response
            sql_query = get_gemini_response(question, prompt)
            
            # Retrieve data from the MySQL database
            columns, response = read_sql_query(sql_query)
            
            df = pd.DataFrame(response, columns=columns)

            # Generate a graph based on the DataFrame
            

            # Convert the figure to JSON for the frontend
            #graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
                
            if 'TotalAmount' in columns or 'SaleDate' in columns or 'ProductName' in df.columns and 'Price' in df.columns :  # Check if 'TotalAmount' exists in columns
                fig = generate_graph(df)
                graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
                
                return jsonify({
                    "success": True,
                    "query": sql_query,
                    "columns": columns,
                    "data": df.to_dict(orient="records"),
                    "graph": graph_json
                })
            else:
                return jsonify({
                    "success": True,
                    "query": sql_query,
                    "columns": columns,
                    "data": df.to_dict(orient="records"),
                    "graph": None
                })
           
            
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    return jsonify({"success": False, "message": "No question provided"})

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
