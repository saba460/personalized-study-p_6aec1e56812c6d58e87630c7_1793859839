"""Run from this directory: python run.py."""
from study_planner import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
