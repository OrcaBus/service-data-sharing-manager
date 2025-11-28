#!/usr/bin/env python3

"""
Big script using snakemd to generate an RMarkdown template for a data summary report.

We then run the RMarkdown file to generate the report.

"""

# Standard imports
from os import environ
from subprocess import run


def main():
    from data_summary_reporting_tools.markdown_helpers import generate_data_summary_report_template
    generate_data_summary_report_template(environ['JOB_ID'])
    render_proc = run(
        [
            "Rscript",
            "-e",
            "rmarkdown::render('data_summary_report.Rmd', output_file = 'data_summary_report.html')"
        ],
        capture_output=True
    )

    if render_proc.returncode != 0:
        print("Error in rendering RMarkdown file")
        print(render_proc.stderr.decode())
        raise Exception("Error in rendering RMarkdown file")


if __name__ == "__main__":
     main()

## Multiple projects over a run
# if __name__ == "__main__":
#     import subprocess
#     from os import environ
#
#     environ['AWS_PROFILE'] = 'umccr-development'
#     environ['AWS_REGION'] = 'ap-southeast-2'
#     environ['DYNAMODB_TABLE_NAME'] = "DataSharingPackagingLookupTable"
#     environ['DYNAMODB_INDEX_NAME'] = 'content'
#     environ['PACKAGE_NAME'] = "test-package"
#     environ['JOB_ID'] = "pkg.01K0R65TY55FX9QF36FVSKC9AX"
#     environ['OUTPUT_URI'] = 's3://data-sharing-artifacts-843407916570-ap-southeast-2/packages/year=2025/month=07/day=22/pkg.01K0R65TY55FX9QF36FVSKC9AX/final/SummaryReport.test-package.html'
#
#     from data_summary_reporting_tools.markdown_helpers import generate_data_summary_report_template
#
#     generate_data_summary_report_template(environ['JOB_ID'])
#
#     subprocess.run(
#         "Rscript -e \"rmarkdown::render('data_summary_report.Rmd', output_file = 'data_summary_report.html')\"",
#         shell=True
#     )
