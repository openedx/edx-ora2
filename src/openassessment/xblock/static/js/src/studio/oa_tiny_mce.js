/* Get tinyMCE comfig */
/* jshint unused:false */
// eslint-disable-next-line no-unused-vars
export const oaTinyMCE = (options) => {
  const CUSTOM_FONTS = 'Default=\'Open Sans\', Verdana, Arial, Helvetica, sans-serif;';
  const STANDARD_FONTS = 'Andale Mono=andale mono,times;'
    + 'Arial=arial,helvetica,sans-serif;'
    + 'Arial Black=arial black,avant garde;'
    + 'Book Antiqua=book antiqua,palatino;'
    + 'Comic Sans MS=comic sans ms,sans-serif;'
    + 'Courier New=courier new,courier;'
    + 'Georgia=georgia,palatino;'
    + 'Helvetica=helvetica;'
    + 'Impact=impact,chicago;'
    + 'Symbol=symbol;'
    + 'Tahoma=tahoma,arial,helvetica,sans-serif;'
    + 'Terminal=terminal,monaco;'
    + 'Times New Roman=times new roman,times;'
    + 'Trebuchet MS=trebuchet ms,geneva;'
    + 'Verdana=verdana,geneva;'
    + 'Webdings=webdings;'
    + 'Wingdings=wingdings,zapf dingbats';

  const getFonts = () => CUSTOM_FONTS + STANDARD_FONTS;
  const baseAssetUrl = options.base_asset_url;
  const staticUrl = '/static/';

  const dataHandler = (key, ...urls) => (data) => {
    if (data[key]) {
      data[key] = window.rewriteStaticLinks(data[key], ...urls);
    }
  };

  const setupTinyMCE = (ed) => {
    ed.on('SaveImage', dataHandler('src', staticUrl, baseAssetUrl));
    ed.on('SaveLink', dataHandler('href', staticUrl, baseAssetUrl));
  };

  const initInstanceCallback = (ed) => {
    ed.setContent(window.rewriteStaticLinks(
      ed.getContent({ no_events: 1 }),
      staticUrl,
      baseAssetUrl,
    ));
    return ed.focus();
  };

  return {
    height: '300',
    font_formats: getFonts(),
    base_url: '/static/studio/js/vendor/tinymce/js/tinymce/',
    theme: 'silver',
    skin: 'studio-tmce5',
    content_css: 'studio-tmce5',
    schema: 'html5',
    convert_urls: false,
    directionality: $('.wrapper-view, .window-wrap').prop('dir'),
    formats: {
      code: { inline: 'code' },
    },
    visual: false,
    plugins: 'link, image, media',
    image_advtab: true,
    toolbar: 'formatselect | fontselect | bold italic underline forecolor | '
      + 'bullist numlist outdent indent blockquote | link unlink image media',
    block_formats: `${gettext('Paragraph')}=p;${gettext('Preformatted')}=pre;${gettext('Heading 3')}=h3;${gettext('Heading 4')}=h4;${gettext('Heading 5')}=h5;${gettext('Heading 6')}=h6`,
    menubar: false,
    statusbar: false,
    valid_children: '+body[style]',
    valid_elements: '*[*]',
    extended_valid_elements: '*[*]',
    invalid_elements: '',
    setup: setupTinyMCE,
    init_instance_callback: initInstanceCallback,
    browser_spellcheck: true,
  };
};

export default oaTinyMCE;
