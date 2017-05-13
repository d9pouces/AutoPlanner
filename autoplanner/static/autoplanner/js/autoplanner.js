function DateTimeShortcutsReinit(root) {
    var inputs = $(root + ' input');
    for (var i = 0; i < inputs.length; i++) {
        var inp = inputs[i];
        if (inp.getAttribute('type') === 'text' && inp.className.match(/vTimeField/)) {
            DateTimeShortcuts.addClock(inp);
            DateTimeShortcuts.addTimezoneWarning(inp);
        }
        else if (inp.getAttribute('type') === 'text' && inp.className.match(/vDateField/)) {
            DateTimeShortcuts.addCalendar(inp);
            DateTimeShortcuts.addTimezoneWarning(inp);
        }
    }
}

function InverseSelection() {
    $('#tasks_table input[type=checkbox]').each(function (index, value) {
        value.checked = !value.checked;
    });
    return false;
}