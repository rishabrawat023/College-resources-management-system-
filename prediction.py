"""
ml/prediction.py
----------------
PLACEHOLDER: shows how booking history could be used to predict resource demand later.

The website does NOT use this file. It works completely without machine learning.
A model needs a lot of real history (at least a few months of bookings) before its
predictions mean anything. With the small sample data this file only prints a message.

Optional install:   pip install pandas scikit-learn
Run from the project folder:   python ml/prediction.py
"""

import os
import sys

# Allow "import database" from the main project folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database

MIN_BOOKINGS_NEEDED = 200   # below this we do not train a model


def load_booking_history():
    """Step 1: read confirmed bookings from MySQL into a pandas table (DataFrame)."""
    import pandas as pd

    rows = database.run_query(
        "SELECT resource_id, date, HOUR(start_time) AS start_hour "
        "FROM bookings WHERE status = 'Confirmed'"
    )
    return pd.DataFrame(rows)


def prepare_demand_table(history):
    """
    Step 2: count bookings per resource, weekday and hour.
    These counts are the "demand" we would like to predict.
    """
    history = history.copy()
    history["weekday"] = history["date"].apply(lambda d: d.weekday())   # 0 = Monday
    demand = history.groupby(["resource_id", "weekday", "start_hour"]).size()
    return demand.reset_index(name="booking_count")


def train_demand_model(demand):
    """Step 3: train a simple model: (resource, weekday, hour) -> expected bookings."""
    from sklearn.ensemble import RandomForestRegressor

    features = demand[["resource_id", "weekday", "start_hour"]]
    target = demand["booking_count"]

    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(features, target)
    return model


def main():
    try:
        history = load_booking_history()
    except ImportError:
        print("pandas is not installed. Run: pip install pandas scikit-learn")
        return

    print(f"Bookings found in the database: {len(history)}")

    if len(history) < MIN_BOOKINGS_NEEDED:
        print(f"Not enough data to train a model (need at least {MIN_BOOKINGS_NEEDED}).")
        print("Keep using the system. When enough real bookings exist, this file can train a model.")
        return

    demand = prepare_demand_table(history)
    model = train_demand_model(demand)

    # Example question: how many bookings do we expect for resource 1 on Monday at 10:00?
    import pandas as pd
    question = pd.DataFrame([{"resource_id": 1, "weekday": 0, "start_hour": 10}])
    print("Expected bookings for resource 1, Monday 10:00:", round(model.predict(question)[0], 2))


if __name__ == "__main__":
    main()
