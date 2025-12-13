# Implementation

## Structure of the project

A complete workflow is implemented for generating musical sequences from symbolic data with Markov chains. It covers dataset preparation, model training and evaluation, sequence generation, and interactive playback, providing both visual and auditory feedback to explore the results.

### Data collection and preprocessing

The pipeline downloads and extracts the MAESTRO dataset, normalizes each MIDI piece to C major or A minor, and converts the piano part into a simplified monophonic token stream. Sequences are organized into train, validation, and test splits with minimal metadata and saved as JSON files. Parallel processing ensures efficient handling of large volumes while producing standardized outputs for modeling.

#### Data collection

`data_collection.py` establishes a workflow for retrieving and preparing an external dataset. It defines local directory paths, ensures that the required storage structure exists, and manages the retrieval of a remote compressed file. Before downloading, it performs a basic existence check to avoid redundant network transfers. Once the file is obtained—or confirmed to be present—the script proceeds to handle subsequent preparation tasks automatically when executed as a standalone module.

A dedicated function unpacks the compressed archive into the designated data directory. The extraction step uses a secure context manager to ensure the archive is opened and closed properly, then fully expands its contents while preserving directory structure.

The dataset retrieved is MAESTRO (MIDI and Audio Edited for Synchronous TRacks and Organization), a large-scale collection of classical piano performances captured with high temporal and expressive fidelity. It comprises recorded performances aligned with their corresponding MIDI representations, enabling analysis of timing, dynamics, and articulation. The MAESTRO dataset spans several years of the International Piano-e-Competition and includes metadata such as composer, piece, year, and performance session.

#### Preprocess

In `preprocess_2.py` is included the `normalize_key` step  that determines the piece’s tonal center by running a key analysis on the parsed MIDI content and then **transposes the entire score to a fixed reference key**: C for major-mode pieces and A for minor-mode pieces. This is done to remove key-level variance across performances so subsequent sequence models see the same pitch relationships regardless of the original key; choosing C major and A minor keeps the relative intervals intact while mapping major/minor modes to common reference tonics, which simplifies learning and reduces the size of the effective pitch-space the pipeline must handle.

The `parse_midi_file` and `process_entry` routine converts a MIDI into a compact, monophonic **token stream** by selecting the piano part, flattening event ordering, and emitting one token per sounding event. For notes it emits the MIDI pitch number; for chords it reduces the chord to its highest pitch and emits that single pitch token; rests and expressive/dynamic information are not represented. The output deliberately omits timing, duration, velocity, and polyphonic structure beyond the highest-voice pitch because **the goal is a simplified sequence of pitch tokens** that is easier and faster to model than a full symbolic-performance representation.

The parallel processing function orchestrates reading the dataset CSV, splitting entries by train/validation/test, and converting each MIDI to a JSON file containing the small metadata block (composer, title, year, split, and original MIDI filename) together with the token list. Conversion is executed with a process pool sized from available CPU cores (CPU count minus one) to maximize throughput while avoiding single-process bottlenecks; existing output files are skipped to make the pipeline idempotent. This design trades per-file fidelity for throughput and standardized outputs that downstream components can consume deterministically.

### Training, validation and testing

Training loads pitch-token sequences from the training split, builds n-th-order Markov chains by recording transition frequencies between n-grams, and converts counts to probabilities, saving each model as JSON with stringified keys. Validation evaluates how well these models generalize to unseen sequences by computing average log-likelihoods. This process provides a scalar measure of model performance across different orders, guiding selection of the most effective configuration.

#### Training

Training begins by loading the token sequences previously generated for the training split. Each JSON file is parsed to **extract only the list of pitch tokens**, ignoring metadata because the training logic requires only the symbolic sequences. The loader aggregates these lists into memory and validates that the folder exists before processing. Invalid or unreadable files are skipped, ensuring that the training phase operates only on clean, tokenized inputs.

The core modeling function **constructs an n-th-order Markov chain** by iterating over each sequence and forming states as n-grams of consecutive tokens. For every state, **it records the frequency of the token that follows it**, building a transition count table. After collecting all counts, it converts them to probabilities so that each state maps to a distribution over possible next tokens. This structure allows the model to understand local pitch patterns of different lengths depending on the chosen order, where higher orders capture longer contextual dependencies at the cost of greater sparsity.

The model is serialized to disk. Because JSON does not support tuple keys, each state is transformed into a comma-joined string before saving. The training loop iterates over several orders, producing separate files for each to allow downstream components to choose the appropriate complexity. This design supports reproducibility and modularity: data loading, model construction, and model persistence are cleanly separated while ensuring that the Markov models are stored in a universally readable format.

#### Validation

The objective of validation is to measure how well a trained model generalizes to data it did not see during training but that still belongs to the same distribution. Validation results guide model selection, helping determine which model order or configuration provides the best balance between capturing meaningful structure and avoiding overfitting.

`validation_2.py` loads the validation token sequences, mirroring the structure used during training. It reads each JSON file, extracts only the token list, and accumulates these sequences in memory. Metadata is intentionally ignored because the evaluation metric compares only the symbolic patterns generated during validation. The loader includes minimal fault tolerance, skipping unreadable files to avoid interrupting the evaluation process, and ensures the folder exists before proceeding.

The model loader reverses the key-stringification performed during training. It reconstructs each state as a tuple by splitting the comma-joined string used to store n-gram keys in JSON. This restores the model to a structure where each state maps to a dictionary of transition probabilities. This format matches the requirements of the likelihood function, which expects direct tuple lookups to evaluate how well the model accounts for each observed continuation in the validation sequences.

Log-likelihood is a numerical measure of how well a probabilistic model explains an observed sequence of events. It is computed by taking the logarithm of the probability the model assigns to each transition in the sequence and summing these log values. Higher log-likelihood indicates that the sequence is more consistent with the model’s learned transition patterns, while lower values signal that the model finds the sequence improbable.

The sequence log-likelihood computation iterates through each n-gram window in a sequence and accumulates log probabilities for each observed transition. When a state or transition is not present in the model (which indicates the model has no learned evidence for that pattern) it applies a large fixed penalty rather than a zero probability to prevent the likelihood from collapsing to negative infinity. This method allows comparison across models of different orders by ensuring they all handle unseen events consistently. The evaluation loop loads every available model order and computes the average log-likelihood across all validation sequences, providing a scalar summary of how well each model explains new data.

#### Testing

The objective of testing is to evaluate the final chosen model on a completely untouched dataset to measure its performance in a realistic, unbiased setting. Unlike validation, which is used for model tuning and comparison, testing provides the definitive assessment of how the selected model behaves on new data and must not influence any model decisions

This script loads a previously trained Markov model and reconstructs its internal structure by converting each comma-separated string key back into an n-gram tuple. That restoration is required because the JSON file stores states as strings, but the evaluation logic depends on tuple-based lookups for efficient retrieval of transition probabilities. The loader remains agnostic to order; instead of requiring it as input, the model’s structure determines it implicitly.

The sequence loader retrieves the test split and extracts only the token list from each JSON file. The output is a collection of pitch-token sequences analogous to those used in training and validation. Metadata is ignored because the evaluation metric only measures how consistent the test sequences are with the statistical patterns captured by the model. The loader includes a small amount of fault tolerance so that malformed or missing files do not interrupt the execution.

The evaluation step averages these log-likelihoods across all test sequences, yielding a single metric that reflects how well the chosen model order explains unseen data. This structure allows the script to test any specified model, here selecting order two after prior observations indicated that it produces more coherent sequences than order one despite slightly lower validation scores.

### Generator and user interface

The Markov generator creates new sequences by transposing a seed to a normalized key, sampling notes from an n-gram model, and sliding a window until the desired length, then transposing back. The interface lets users set order, measures, key, and input seed notes on a pentagram, showing output visually and in ABC notation with play and reset options. Playback synthesizes the sequence with sine waves and an ADSR envelope, concatenating notes and streaming audio for immediate feedback.

#### Markov generator

The main function of the `markov_generator` script is the logics behind the generation of new musical sequences from a trained model while preserving the musical key requested by the user. It begins by establishing a mapping between every supported key and a semitone offset that aligns all inputs to a common reference in C major or A minor. Transposition is performed using simple pitch arithmetic, ensuring that note tokens remain compatible with the “NOTE_[pitch]” format established during preprocessing.

The generation function validates user inputs to ensure that the model order, seed length, number of measures, and requested key are coherent. It then loads the appropriate model, making use of a global cache to avoid repeated deserialization and improve performance during multiple generations within the same session. Sampling is performed through **weighted random selection**, meaning the generator respects the learned transition probabilities instead of producing deterministic output. The generation process uses a **sliding window** aligned to the model’s order, producing new notes until the requested length is reached or an unseen state interrupts generation.

Key handling is central to this script’s purpose. Before generation begins, the seed is transposed into the model’s normalized tonal center, ensuring that the transition probabilities remain meaningful. After the full sequence has been generated in this normalized space, it is transposed back into the user’s requested key so that the final output maintains its intended harmonic identity.

#### User interface

The interface allows the user to select the Markov chain order, which determines the length of the n-grams used to generate sequences. Higher orders capture longer contextual patterns, while lower orders produce simpler, more random sequences. This selection directly influences the coherence and stylistic consistency of the generated output.

Users can specify the number of measures to generate, with each measure corresponding to four notes. This control translates the desired musical length into a target number of notes for the generation algorithm, ensuring that output sequences match the user’s intended composition size.

The pentagram provides an interactive way to input seed notes equal to the chosen Markov order. Double-clicking adds a note at the clicked position, clicking allows changing the accidental, and right-clicking deletes a note. These actions define the initial state of the sequence, which the generation process uses to produce subsequent notes according to the learned transition probabilities.

After setting the parameters and seed, the `Generate` button produces new notes that appear on the pentagram and in ABC notation for textual representation. The `Play` button allows immediate auditory feedback of the generated sequence, and the `Reset` button clears the pentagram for a new composition. This design combines visual, textual, and auditory outputs to provide full control and immediate evaluation of the generated sequences.

#### Playback

This module provides a lightweight mechanism for converting MIDI note values into audible output. The synthesis step creates a pure sine tone shaped by a minimal ADSR envelope with short attack and release phases to eliminate abrupt clicks and produce a smoother onset and decay. The resulting waveform for each note is generated at the specified sampling rate and scaled to avoid clipping.

Once synthesized, all note waveforms are concatenated into a single audio buffer, preserving their sequential structure. The playback function then streams this buffer through the audio device using the sounddevice library, blocking execution until playback is complete.

## Possible shortcomings and suggestions for improvement

The current approach unifies all pieces into a single normalized key, which simplifies modeling but may limit the model’s ability to capture mode-specific patterns. A possible improvement is to separate the dataset into major and minor subsets, allowing dedicated models to learn more coherent transition structures within each tonal context. Another enhancement would be to adopt a richer preprocessing strategy that preserves additional musical information instead of reducing everything to a monophonic pitch stream. This would provide the model with a more expressive representation of musical structure.

Model capacity is also a limiting factor: n-gram Markov chains cannot capture long-range dependencies or stylistic nuances. Using a larger or more advanced model could significantly improve generation quality and musical coherence. Finally, improving the symbolic vocabulary to include duration values (not only pitch) would enable the system to generate more realistic rhythmic structures rather than sequences of uniform note lengths. This would bring the output closer to the expressive variability present in real musical performances.

## Time and spce complexities

The system’s core components exhibit predictable time and space behaviors derived from their underlying algorithms. Building an n-th-order Markov chain operates in O(N · n) time, where N is the total number of tokens in the training set, because each sliding window of length n is processed once, and in O(S · A) space, where S is the number of unique n-gram states and A the average number of possible next tokens. Sequence generation runs in O(L) time for L produced notes, as each step performs a constant-time lookup and weighted sampling.

## Use of large language models

ChatGPT was used primarily for error correction and partial guidance in establishing an appropriate development workflow. The final system design, algorithmic choices, and code organization were independently developed following standard software developement methodologies.

## Sources

[1] C. Hawthorne, A. Stasyuk, A. Roberts, I. Simon, C.-Z. A. Huang, S. Dieleman, E. Elsen, J. Engel, and D. Eck, “Enabling factorized piano music modeling and generation with the MAESTRO dataset,” in Proc. Int. Conf. Learn. Representations (ICLR), 2019. [Online]. Available: https://openreview.net/forum?id=r1lYRjC9F7

[2] Markov Chains explained visually, Setosa.io. [Online]. Available: https://setosa.io/ev/markov-chains

[3] Markov Chain, GeeksforGeeks. [Online]. Available: https://www.geeksforgeeks.org/markov-chain/

[4] Chapter 16: Introduction to Markov Chains, Learn Probability. [Online]. Available: https://snowch.github.io/learn_probability/chapter_16.html