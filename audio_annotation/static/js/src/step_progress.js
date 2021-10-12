function load_steps(last, previousfunc, previous_labels_so_far, my) {
    $('#steps').empty();

    for (var i = 0; i < previous_labels_so_far.length; i++) {

        switch (previous_labels_so_far[i]) {
            case true:
                $('#steps').append([
                    $('<li/>', {
                        "class": "step step-success", "click": function () {
                            previousfunc($(this).text(), my)
                        }
                    }).append([
                        $('<div/>', {"class": "step-content"}).append([
                            $('<span/>', {"class": "step-circle"}).append([
                                $('<i/>', {"class": "fa fa-check"})
                            ]),
                            $('<span/>', {"class": "step-text", "text": i + 1})
                        ])
                    ]),
                ]);
                break;
            case false:
                $('#steps').append([
                    $('<li/>', {
                        "class": "step step-false", "click": function () {
                            previousfunc($(this).text(), my)
                        }
                    }).append([
                        $('<div/>', {"class": "step-content"}).append([
                            $('<span/>', {"class": "step-circle"}).append([
                                $('<i/>', {"class": "fa fa-times"})
                            ]),
                            $('<span/>', {"class": "step-text", "text": i + 1})
                        ])
                    ]),
                ]);
                break;
            case 'flag':
                $('#steps').append([
                    $('<li/>', {
                        "class": "step step-flag", "click": function () {
                            previousfunc($(this).text(), my)
                        }
                    }).append([
                        $('<div/>', {"class": "step-content"}).append([
                            $('<span/>', {"class": "step-circle"}).append([
                                $('<i/>', {"class": "fa fa-exclamation"})
                            ]),
                            $('<span/>', {"class": "step-text", "text": i + 1})
                        ])
                    ]),
                ]);
                break;
            case 'current':
                $('#steps').append([
                    $('<li/>', {"class": "step step-active", "id": "current"}).append([
                        $('<div/>', {"class": "step-content"}).append([
                            $('<span/>', {"class": "step-circle"}).append([
                                $('<i/>', {"class": "fa fa-question", "id": "questionmark"})
                            ]),
                            $('<span/>', {"class": "step-text", "text": i + 1})
                        ])
                    ]),
                ]);

                break;
            default:
                if (latest + 1 === i + 1) {
                    $('#steps').append([
                        $('<li/>', {
                            "class": "step", "click": function () {
                                previousfunc($(this).text(), my)
                            }
                        }).append([
                            $('<div/>', {"class": "step-content"}).append([
                                $('<span/>', {"class": "step-circle"}).append([
                                    $('<i/>', {"class": "fa fa-question"})
                                ]),
                                $('<span/>', {"class": "step-text", "text": i + 1})
                            ])
                        ]),
                    ]);
                } else {
                    $('#steps').append([
                        $('<li/>', {"class": "step step-not-allowed"}).append([
                            $('<div/>', {"class": "step-content"}).append([
                                $('<span/>', {"class": "step-circle"}),
                                $('<span/>', {"class": "step-text", "text": i + 1})
                            ])
                        ]),
                    ]);
                }
        }
    }

    if (last === true) {
        $('#steps').append([
            $('<li/>', {"class": "step step-active"}).append([
                $('<div/>', {"class": "step-content"}).append([
                    $('<span/>', {"class": "step-circle finish-star"}).append([
                        $('<i/>', {"class": "fa fa-star"})
                    ]),
                ])
            ]),
        ]);
    } else {
        if (latest === batch_size) { // star should be clickable
            $('#steps').append([
                $('<li/>', {
                    "class": "step", "id": "star", "click": function () {
                        show_batch_end(my);
                        $("#star").addClass("step-active");
                        current_passed(previousfunc, my)
                    }
                }).append([
                    $('<div/>', {"class": "step-content star_hoverable"}).append([
                        $('<span/>', {"class": "step-circle star "}).append([
                            $('<i/>', {"class": "fa fa-star"})
                        ]),
                    ])
                ]),
            ]);
        } else {
            $('#steps').append([
                $('<li/>', {"class": "step star_unhoverable"}).append([
                    $('<div/>', {"class": "step-content"}).append([
                        $('<span/>', {"class": "step-circle star "}).append([
                            $('<i/>', {"class": "fa fa-star"})
                        ]),
                    ])
                ]),
            ]);
        }
    }

}

function current_passed(previousfunc, my) {
    var x = parseInt($("#current").text())
    $("#current").removeClass("step-active");
    $("#current").addClass("step-success");
    $("#current").click(function () {
        previousfunc(x, my)
    });

    $("#questionmark").removeClass("fa-question");
    $("#questionmark").addClass("fa-check");
}


