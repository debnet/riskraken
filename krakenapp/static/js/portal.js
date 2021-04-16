
function updateTroops() {
    let reserve = parseInt($('#reserve').val());
    let used = 0;
    $('input.troops').each((i, e) => {
        let value = parseInt($(e).val());
        let initial = parseInt($(e).data('initial'));
        used += (value - initial);
    }).each((i, e) => {
        let value = parseInt($(e).val());
        let maximum = value + (reserve - used);
        $(e).attr('max', maximum);
        $(e).attr('aria-valuemax', maximum);
    });
    let remaining = reserve - used;
    $('#remaining').removeClass('badge-primary').removeClass('badge-danger').text(remaining);
    if (remaining > 0) $('#remaining').addClass('badge-primary');
    else $('#remaining').addClass('badge-danger');
}

$(function() {
    $('input.troops').keypress(function(e) {
        // e.preventDefault();
    }).change(function() {
        updateTroops();
    });
    updateTroops();
    $('[data-toggle="tooltip"]').tooltip();
});
