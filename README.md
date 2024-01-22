# RAG Example using Vector Search in MongoDB Atlas

This README provides instructions on how to set up and run the code for preparing chat data from PDF files and storing it in your MongoDB Atlas instance. Ensure the instructions are followed accurately for successful execution.

## Step 1: Create a MongoDB Atlas Instance

1. Create a MongoDB Atlas instance if you don't already have one.
2. Set the desired names for your database and collection. For this code, the suggested names are:
   - Database Name: "demo_RAG_PDF"
   - Collection Name: "patientGuides"

## Step 2: Configure Environment Variables

Create a `.env` file in your project directory and add the following key-value pairs:

```
OPENAI_API_KEY="your-key"
MONGODB_CONNECTION_STRING="mongodb+srv://YOUR_CONNECTION_STRING"
```

Replace "your-key" with your actual OpenAI API key and "YOUR_CONNECTION_STRING" with your actual MongoDB Atlas connection string.

## Step 3: Install Python Dependencies

Run the following command to install the required Python dependencies:

```
pip3 install pymongo openai certifi PyPDF2 python-dotenv langchain streamlit pandas
```

## Step 4: Execute the Code
To run the code, execute the following command:

```
streamlit run chat-data-prep-pdf-mongo.py
```

## Step 5: Add a Vector Search Index in MongoDB Atlas
Go to MongoDB Atlas and navigate to Atlas Search.

Click "Create Search Index" and select JSON Editor under Atlas Vector Search.
Choose the database and collection you created earlier.
Set "default" as the Index Name.
Paste the following index definition in the edit box:
```
{
  "fields": [
    {
      "type": "vector",
      "path": "vector_embedding",
      "numDimensions": 1536,
      "similarity": "euclidean"
    }
  ]
}
```

Click "Next" and then "Create Search Index."

## Step 6: Running the Code
You can now execute the code again using:

```
streamlit run RAG-pdf.py
```

## Notes about the functionality:

After running the code, you can load text chunks from PDF files into Atlas by typing "docs" as the directory name.
You can then ask questions like:

"What does stage 4 cancer mean?, Is it curable?, Which are the most common treatments?"





