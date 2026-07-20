from lob_reproductions.cli import main

PROFILES = (
    "gould_bonart_2015_paper",
    "gould_bonart_2015_chronological_audit",
    "deeplob_ieee_2019",
    "deeplob_author_tf2_ff14d7c",
    "deeplob_author_tf2_corrected_dropout_audit",
    "deeplob_author_pytorch_ff14d7c",
    "tlob_paper_arxiv_2502_15757",
    "tlob_author_repo_f1c0af4",
    "tlob_corrected_bin_audit",
    "mlplob_paper_arxiv_2502_15757",
    "mlplob_author_repo_f1c0af4",
    "sirignano_cont_2019_paper_constrained",
)


if __name__ == "__main__":
    raise SystemExit(max(main(["smoke", "--profile", profile]) for profile in PROFILES))
