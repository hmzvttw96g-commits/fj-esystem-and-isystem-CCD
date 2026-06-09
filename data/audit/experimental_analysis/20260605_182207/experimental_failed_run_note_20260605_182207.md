# Failed Experimental Run Note - 20260605_182207

This run was interrupted before report and manifest generation because the first version of `scripts/experimental_analysis_pipeline.py` used pandas `to_markdown`, which required the optional `tabulate` dependency.

The script was fixed to use an internal Markdown table formatter. This partial run did not update latest files and should not be used as the formal experimental analysis result.

The formal successful run is:

`20260605_182254`
