"""Zero-curve construction, validation and model risk.

The package is organised as a straight line from raw observations to published
curve, so that every number in ``outputs/`` can be traced back to a decision:

``io``            strict schema loading with an audit of unparseable cells
``validation``    read-only defect detection (27 flags), no data is changed here
``cleaning``      the audited corrections, exclusions and weights
``conventions``   day-count-free schedule and rate/discount conversions
``instruments``   the immutable calibration instrument
``pricing``       cash flows and model quotes, scalar and vectorised
``curve``         discount-curve representations (piecewise-flat and spline forwards)
``models``        the bootstrap baseline, the penalised robust spline, the screen
``holdout``       maturity-blocked validation split and the model selection rule
``risk``          DV01 and key-rate sensitivities with an analytic cross-check
``sensitivity``   stability and perturbation studies
``workflow``      the end-to-end run
``outputs``       the machine-readable output contract
``charts``        the figures
``report``        the self-contained HTML research report
``cli``           the mandated command-line entry point
"""

__version__ = "1.0.0"
