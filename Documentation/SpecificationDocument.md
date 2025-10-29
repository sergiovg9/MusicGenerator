# Software specification

## General

The project will be developed using the **Python** programming language and will be conducted in **English** by an exchange student enrolled in the Bachelor's program in **Computer Science**.

This project focuses on **music generation** using machine learning principles. The program reads training data in the form of MIDI files, extracts note sequences, and learns the statistical relationships between them using a Markov chain model.

The system stores its training data in a trie data structure, which allows efficient lookup of possible continuations for any given sequence. 

## Core

The implementation supports arbitrary-order **Markov chains**, enabling flexible control over how much past context influences melody generation. The problem addressed is how to create coherent and stylistically consistent melodies that resemble human-composed music through algorithmic sequence learning.

The core of the project lies in building and training the Markov chain with trie-based storage, which forms the foundation for the generative process, while additional tools handle data preprocessing and melody playback.

## Dependencies

The program takes MIDI files as input, processes them with the help of libraries such as music21, and encodes the notes into sequences of pitches and durations. These sequences are used to train the Markov model, which can later generate new melodies based on user prompts or random seeds. The main data sources will include the  MAESTRO Dataset. 