# Streak Tracker Application

This is a desktop application built with Python and Tkinter for tracking streaks of activities or habits. It allows users to manage multiple modules, add or delete streak dates individually or in ranges, and visualize streak progress over time with an interactive graph.

## Features

- Manage multiple modules to track different streaks separately.
- Add or delete individual streak dates.
- Add or delete ranges of streak dates.
- Visualize streak progress over time with a matplotlib graph embedded in the GUI.
- Highlights highest streaks and streak breaks.
- Stores data persistently in an SQLite database (`streaks.db`).

## Technologies Used

- Python 3
- Tkinter for GUI
- SQLite for data storage
- Matplotlib for plotting streak graphs
- tkcalendar for date selection widgets

## Development Notes

This project was an exploration of vibe coding with Blackbox AI, experimenting with interactive AI-assisted coding workflows. The entire program, including this README file, was written by Blackbox AI based on user prompts only. The development process involved multiple iterations to get the code working correctly, including fixing several errors along the way. Limitations of this tool include that rollback does not always work perfectly, and at times code editing can crash or be slow. Careful testing and validation were necessary during development.



## Usage

Run the `streak_tracker.py` script with Python 3 to launch the application:

```bash
python streak_tracker.py
```

## License

This project is licensed under the terms specified in the LICENSE file.
