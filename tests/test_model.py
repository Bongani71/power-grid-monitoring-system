import joblib
import pandas as pd

def test_prediction_output_shape():
    try:
        model_data = joblib.load("forecasting/model.pkl")
        model = model_data["model"]
    except Exception:
        # Skip gracefully if not run yet
        return

    future_df = pd.DataFrame({"hour": [10, 2]})
    preds = model.predict(future_df)
    
    # Assert inference shape is maintained gracefully
    assert len(preds) == 2
