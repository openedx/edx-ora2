import sass

BASE_DIR = 'openassessment/xblock/static/'
sass.compile(
    dirname=(BASE_DIR+'sass', BASE_DIR+'css'),
    include_paths=[BASE_DIR+'sass/vendor/bi-app'],
    output_style='compressed',
)
