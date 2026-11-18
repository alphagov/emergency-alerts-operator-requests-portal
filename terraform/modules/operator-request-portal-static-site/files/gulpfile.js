'use strict';
const fs = require('fs');
const { src, dest, parallel, series } = require('gulp');
const sass = require('gulp-sass')(require('sass'));

const govuk = 'node_modules/govuk-frontend/dist/govuk/';
const govukAssets = govuk + 'assets/';
const dist = 'assets/';

const fonts = () =>
  src(govukAssets + 'fonts/**/*', { encoding: false }).pipe(dest(dist + 'fonts/'));

const images = () =>
  src(govukAssets + 'images/**/*', { encoding: false }).pipe(dest(dist + 'images/'));

const manifest = () =>
  src(govukAssets + 'manifest.json').pipe(dest(dist));

const stylesheets = () =>
  src('stylesheets/application.scss')
    // quietDeps silences deprecation warnings from govuk-frontend's own Sass, as advised here:
    // https://frontend.design-system.service.gov.uk/import-css/#silence-deprecation-warnings-from-dependencies-in-dart-sass
    .pipe(sass.sync({ loadPaths: ['.'], includePaths: ['.'], quietDeps: true }).on('error', sass.logError))
    .pipe(dest(dist + 'stylesheets/'));

const javascripts = () =>
  src(govuk + 'govuk-frontend.min.js').pipe(dest(dist + 'javascripts/'));

const clean = (done) => {
  fs.rmSync(dist, { recursive: true, force: true });
  done();
};

exports.default = series(clean, parallel(fonts, images, manifest, stylesheets, javascripts));
