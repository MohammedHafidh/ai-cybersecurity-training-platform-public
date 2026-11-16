# Brute force

## Concept

Online password guessing involves repeated attempts to authenticate with guessed credentials. The lab represents this with SSH password events. Repeated failures can also come from ordinary retries, so the training rule's alert is an indicator to inspect.

## Interpreting the lab evidence

The frozen authentication rule counts failed password events in a fixed 60-second window for the same run, source IP, and target. It flags a window at three failures. Check the observed count, window, and linked event IDs. A failed attempt or a rule alert alone cannot establish successful access or the user's intent.
