'use strict';
const { src, pipe, dest, parallel } = require('gulp');
const plugins = {}
plugins.sass = require('gulp-sass')(require('sass'));
const paths = {
  node_modules: 'node_modules/',
  dist: 'assets/',
  govuk_frontend: 'node_modules/govuk-frontend/dist/',
};
const copy = {
  govuk_frontend: {
    fonts: () => {
      return src(paths.govuk_frontend + 'govuk/assets/fonts/**/*', {encoding: false})
        .pipe(dest(paths.dist + 'fonts/'));
    },
    images: () => {
      return src(paths.govuk_frontend + 'govuk/assets/rebrand/images/**/*', {encoding: false})
        .pipe(dest(paths.dist + 'images/'));
    },
    stylesheets: () => {
      return src(paths.govuk_frontend + 'govuk/*.scss')
      // Silencing deprecation warnings from govuk-frontend scss, as advised to here
      // https://frontend.design-system.service.gov.uk/import-css/#silence-deprecation-warnings-from-dependencies-in-dart-sass
        .pipe(plugins.sass.sync({quietDeps: true, silenceDeprecations: ["import"]})
        .on('error', plugins.sass.logError))
        .pipe(dest(paths.dist + 'stylesheets/'));
    },
  }
};
const defaultTask = parallel(
  copy.govuk_frontend.fonts,
  copy.govuk_frontend.images,
  copy.govuk_frontend.stylesheets
);
exports.default = defaultTask;