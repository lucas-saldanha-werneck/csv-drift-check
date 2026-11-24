# csv-drift-check

Independent demo, not affiliated with Oowlish (cliente não diz).

A small Python command that compares two CSV files, an old snapshot and a new one, and lists what changed in a way that can break a data pipeline downstream: dropped or added columns, a column whose type changed, a jump in empty values, a big change in row count, duplicate keys, and keys that disappeared.

It is about 150 lines of standard-library Python. I wrote it as a sketch of the first check I would put in front of a pipeline that reads files from a client system.

## Run it

```
pip install -e ".[dev]"
csv-drift-check examples/orders_monday.csv examples/orders_tuesday.csv --key order_id
```

The exit code is 0 when there is no error, 1 when there is at least one error, and 2 when a file or the key column cannot be read. Warnings do not change the exit code.

Options: `--key` (column that must be unique), `--null-jump` (default 0.10), `--row-change` (default 0.20).

## Example

The two files in `examples/` are invented sample orders. Tuesday's export adds a `channel` column, and one order now appears twice (once per channel). The report shows:

| Severity | Finding |
|---|---|
| warn | column added: channel |
| error | type changed in 'amount': float -> mixed |
| error | 1 duplicate value(s) in key 'order_id' |
| warn | 1 key(s) from the old snapshot are missing |

The new column is harmless on its own. The duplicate order is the real problem: a new column in the source brought a repeated row, and a count or a sum downstream would be wrong.

## What was tested

- 9 offline tests with pytest, no network. They cover type inference, column types, profiling, a missing key column, schema and type changes, null-rate and row-count changes, the no-drift case, CLI exit codes, and the two example files above.
- The test run in CI is `pytest -q` on Python 3.12, and I also ran it locally on Python 3.15.

## What was not tested

- Large files. The code reads the whole key set into memory, and I did not measure it on anything bigger than the examples.
- Real client data. Every file here is invented.
- Other encodings and delimiters. It assumes UTF-8 and commas.
- Dates in formats other than ISO (`2026-11-02`). They are read as strings.
- Python 3.10 and 3.11 are declared as supported but I did not run them.
