import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

import joblib


# Load dataset
data = pd.read_csv("dataset.csv")


# Input and output
X = data["description"]
y = data["category"]


# Convert text into numbers
vectorizer = TfidfVectorizer()

X_vectorized = vectorizer.fit_transform(X)


# Create Machine Learning model
model = LogisticRegression(max_iter=1000)


# Train the model
model.fit(X_vectorized, y)


# Save the model
joblib.dump(model, "expense_model.pkl")

# Save the vectorizer
joblib.dump(vectorizer, "vectorizer.pkl")


print("Model training completed successfully!")
print("Model saved as expense_model.pkl")
print("Vectorizer saved as vectorizer.pkl")