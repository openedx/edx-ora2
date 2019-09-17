
/**
 *
 * A helper function to utilize DateUtils.
 **/

OpenAssessment.DateTimeFactory = function(element) {
    this.element = element;
};

OpenAssessment.DateTimeFactory.prototype = {

    apply: function() {
        var dtFactory = this;
        $('.ora-datetime', this.element).each(function() {
            dtFactory.elementApply($(this));
        });
    },

    determineContext: function(el) {
        var context;
        context = {
            datetime: el.data('datetime'),
            timezone: el.data('timezone'),
            language: el.data('language'),
            format: '',
        };
        return context;
    },

    determineDateToken: function(el) {
        var dtFactory = this;
        var dateToken = 'date';
        if (dtFactory.isValid(el.data('datetoken'))) {
            dateToken = el.data('datetoken');
        }
        return dateToken;
    },

    elementApply: function(el) {
        var dtFactory = this;
        (function(require) {
            require([
                'jquery',
                'edx-ui-toolkit/js/utils/date-utils',
                'edx-ui-toolkit/js/utils/string-utils',
            ], function($, DateUtils, StringUtils) {
                var context;
                var localTimeString;
                var displayDatetime;
                var interpolateDict = {};

                if (dtFactory.isValid(el.data('datetime'))) {
                    context = dtFactory.determineContext(el);
                    if (dtFactory.isValid(el.data('format'))) {
                        context.format = DateUtils.dateFormatEnum[el.data('format')];
                    }

                    localTimeString = DateUtils.localize(context);

                    interpolateDict[dtFactory.determineDateToken(el)] = localTimeString;

                    if (dtFactory.isValid(el.data('string'))) {
                        displayDatetime = StringUtils.interpolate(
                            el.data('string'),
                            interpolateDict
                        );
                    } else {
                        displayDatetime = localTimeString;
                    }
                } else {
                    displayDatetime = StringUtils.interpolate(
                        el.data('string'),
                        interpolateDict
                    );
                }
                el.text(displayDatetime);
            }
            );
        }).call(this, require || RequireJS.require);
    },

    isValid: function(candidateVariable) {
        return candidateVariable !== undefined &&
            candidateVariable !== '' &&
            candidateVariable !== 'Invalid date' &&
            candidateVariable !== 'None';
    },
};
