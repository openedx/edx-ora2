/**
Utilities for reading / writing fields.
**/
OpenAssessment.Fields = {
    stringField: function(sel, value) {
        if (typeof(value) !== "undefined") { sel.val(value); }
        return sel.val();
    },

    datetimeField: function(sel, value) {
        if (typeof(value) !== "undefined") { sel.val(value); }
        var fieldValue = sel.val();
        return (fieldValue !== "") ? fieldValue : null;
    },

    intField: function(sel, value) {
        if (typeof(value) !== "undefined") { sel.val(value); }
        return parseInt(sel.val(), 10);
    },

    booleanField: function(sel, value) {
        if (typeof(value) !== "undefined") { sel.prop("checked", value); }
        return sel.prop("checked");
    },
};
