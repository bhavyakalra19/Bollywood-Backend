// location_autocomplete.js
(function($) {
    $(document).ready(function() {
        var $input = $("#id_location_option");
        if ($input.length) {
            $input.autocomplete({
                source: function(request, response) {
                    $.ajax({
                        url: "/admin/posts/post/location-autocomplete/",
                        dataType: "json",
                        data: {
                            term: request.term
                        },
                        success: function(data) {
                            response(data.results.map(function(item) {
                                return {
                                    label: item.text,
                                    value: item.text
                                };
                            }));
                        }
                    });
                },
                minLength: 1
            });
        }
    });
})(django.jQuery);