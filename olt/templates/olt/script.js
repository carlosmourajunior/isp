$(document).ready(function () {
    $(".open-reset_slot_modal").click(function () {
        $('#bookId').val($(this).data('id'));
        $('#reset_slot_modal').modal('show');
    });
});