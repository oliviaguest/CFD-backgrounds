# CFD background stimuli generation

This code takes input images from the [Chicago Face Database](https://chicagofaces.org/) (which must have had their backgrounds rendered transparent from the original white).
It then combines them with some pre-set backgrounds to create stimuli that have a person in the foreground and a specific environemnt in the background in every possible combination.


Please fill in the directories in `directories.py`.

To run with a ratio of, e.g., 0.17 send the `-r` flag followed by `0.17`:
```
python create_stimuli.py -r 0.17
```

Once the script has run, the stimuli will be in the directory you have chosen along with a CSV file: `stimuli.csv`, which contains useful details per stimulus. 
