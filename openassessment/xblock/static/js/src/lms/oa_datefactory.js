import DateUtils from 'edx-ui-toolkit/src/js/utils/date-utils';
import StringUtils from 'edx-ui-toolkit/src/js/utils/string-utils';
/**
 *
 * A helper function to utilize DateUtils.
 * */
export class DateTimeFactory {
  constructor(element) {
    this.element = element;
  }

  apply() {
    const dtFactory = this;
    $('.ora-datetime', this.element).each(function () {
      dtFactory.elementApply($(this));
    });
  }

  determineContext(el) {
    const context = {
      datetime: el.data('datetime'),
      timezone: el.data('timezone'),
      language: el.data('language'),
      format: '',
    };
    return context;
  }

  determineDateToken(el) {
    const dtFactory = this;
    let dateToken = 'date';
    if (dtFactory.isValid(el.data('datetoken'))) {
      dateToken = el.data('datetoken');
    }
    return dateToken;
  }

  elementApply(el) {
    const dtFactory = this;
    let context;
    let localTimeString;
    let displayDatetime;
    const interpolateDict = {};

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
          interpolateDict,
        );
      } else {
        displayDatetime = localTimeString;
      }
    } else {
      displayDatetime = StringUtils.interpolate(
        el.data('string'),
        interpolateDict,
      );
    }
    el.text(displayDatetime);
  }

  isValid(candidateVariable) {
    return candidateVariable !== undefined
            && candidateVariable !== ''
            && candidateVariable !== 'Invalid date'
            && candidateVariable !== 'None';
  }
}

export default DateTimeFactory;
