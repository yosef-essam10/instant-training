import os
import pandas as pd

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "courses.csv")

_df_cache = None


def _load():
    global _df_cache
    if _df_cache is None:
        _df_cache = pd.read_csv(DATA_PATH)
    return _df_cache


def get_all_courses():
    df = _load()
    return df.to_dict(orient="records")


def search_courses(keyword: str):
    df = _load()
    keyword = str(keyword).strip().lower()
    if not keyword:
        return get_all_courses()
    mask = (
        df["track"].str.lower().str.contains(keyword, na=False)
        | df["course_name"].str.lower().str.contains(keyword, na=False)
        | df["description"].str.lower().str.contains(keyword, na=False)
    )
    result = df[mask]
    if result.empty:
        return []
    return result.to_dict(orient="records")


def get_free_courses():
    df = _load()
    result = df[df["is_free"] == True]
    return result.to_dict(orient="records")


def compare_tracks(track_a: str, track_b: str):
    df = _load()
    a = df[df["track"].str.lower() == str(track_a).strip().lower()]
    b = df[df["track"].str.lower() == str(track_b).strip().lower()]
    return {
        track_a: a.to_dict(orient="records"),
        track_b: b.to_dict(orient="records"),
    }
