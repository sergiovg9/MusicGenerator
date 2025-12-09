# Music Generator

## User Guide

This project can be set up using Poetry or pip with `requirements.txt`. Follow the instructions below.

### System Requirements

Python version: 3.10 or higher

Dependencies: See requirements.txt (or use poetry install if using Poetry)

Minimum disk space: ~1.5 GB to run all scripts

RAM: At least 4 GB recommended

### Initializing dependencies

#### Using Poetry

1. Install Poetry if needed:

For Windows (PowerShell)
> (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

For Linux/macOS
> curl -sSL https://install.python-poetry.org | python3 -


2. Install dependencies and create a virtual environment:

> poetry install

3. Activate the Poetry shell (optional):

> poetry shell

#### Using pip

1. Create a virtual environment (recommended):

> python -m venv venv

2. Activate the virtual environment:

For Windows (PowerShell)
> venv\Scripts\activate

For Linux/macOS
> source venv/bin/activate

3. Install dependencies from requirements.txt:

> pip install -r requirements.txt

### Running the User Interface Only

To launch the GUI for **music generation** run the `main` UI script:

> python src\3-Generator_and_UI\main.py

#### How to Use the Interface

Select the order of the Markov chain.

Choose the number of measures (each measure contains 4 notes).

Choose the musical key.

Add seed notes equal to the Markov chain order:
- Double-click on the pentagram to add a note at the clicked position.
- Click a note to change its accidental (#).
- Right-click to delete a note.

Click the `Generate` button to fill the pentagram with new notes.

Generated notes will appear on the pentagram and in ABC notation below it.

Use the `Play` button to listen to the generated sequence.

Click `Reset` to clear all notes.

### Running All Scripts (Full Workflow)

To train, validate, and test models from scratch, the scripts must be executed in the following order:

1. Data Collection – Collect the raw MIDI dataset:

> python src\1-Data_collection_and_preprocessing\1-data_collection.py

2. Preprocessing – Prepare data for training:

> python src\1-Data_collection_and_preprocessing\2-preprocess.py

3. Training – Train the models:

> python src\2-Training_Validation_Testing\1-training.py

4. Validation – Validate the trained models:

> python src\2-Training_Validation_Testing\2-validation.py

5. Testing – Test the trained models:

> python src\2-Training_Validation_Testing\3-testing.py

6. Run the UI / Music Generator – After training, launch the GUI:

The main.py script in the UI folder internally calls the Markov generator and playback modules

> python src\3-Generator_and_UI\main.py

## File and folder overview

`src/1-Data_collection_and_preprocessing/` – Scripts for data collection and preprocessing

`src/2-Training_Validation_Testing/` – Scripts for training, validation, and testing

`src/3-Generator_and_UI/` – User interface, Markov generator, and playback scripts

`models/` – Saved Markov chain models

`outputs/` – Generated token sequences (train, validation, test)

`data/` – Original and processed MIDI datasets

## Unit testing

Every stage of the workflow counts with its own Testing folder. That is why every stage's testing has to be run separetely:

> pytest src\1-Data_collection_and_preprocessing

> pytest src\2-Training_Validation_Testing

> pytest src\3-Generator_and_UI

## Documentation

* [Specification document](./Documentation/SpecificationDocument.md)
* [Implementation document](./Documentation/ImplementationDocument.md)
* [Testing document](./Documentation/TestingDocument.md)

### Weekly reports
* [Weekly Reports](./Documentation/WeeklyReports)
* [Weekly Report 1](./Documentation/WeeklyReports/WeeklyReport1.md)
* [Weekly Report 2](./Documentation/WeeklyReports/WeeklyReport2.md)
* [Weekly Report 3](./Documentation/WeeklyReports/WeeklyReport3.md)
* [Weekly Report 4](./Documentation/WeeklyReports/WeeklyReport4.md)
* [Weekly Report 5](./Documentation/WeeklyReports/WeeklyReport5.md)
* [Weekly Report 6](./Documentation/WeeklyReports/WeeklyReport6.md)
* [Weekly Report 7](./Documentation/WeeklyReports/WeeklyReport7.md)

## Dataset Information

This project uses the MAESTRO dataset (MIDI and Audio Edited for Synchronous TRacks and Organization), created by Google Magenta.
The dataset contains over 200 hours of virtuosic piano performances with aligned MIDI and audio recordings.

The MAESTRO dataset is available at:

https://magenta.withgoogle.com/datasets/maestro