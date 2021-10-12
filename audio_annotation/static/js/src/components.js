'use strict';

/*
 * Purpose:
 *   Used to create the timestamps of segment start and end times and play bar
 * Dependencies:
 *   jQuey, audio-annotator.css
 */

var Util = {
    // Convert seconds to timestamp string
    secondsToString: function (seconds) {
        if (seconds === null) {
            return '';
        }
        if (seconds >= 10) {
            return seconds.toFixed(3);
        } else {
            return seconds.toFixed(3);
        }
    },

    // Return input elements that will contain the start, end and duration times of a sound segment
    createSegmentTime: function () {
        var timeDiv = $('<div>', {class: 'time_segment'});

        var start = $('<span>', {text: 'Start:'});
        var startInput = $('<input>', {
            type: 'text',
            class: 'form-control start',
            readonly: true
        });
        var end = $('<span>', {text: 'End:'});
        var endInput = $('<input>', {
            type: 'text',
            class: 'form-control end',
            readonly: true
        });

        var duration = $('<span>', {text: 'Duration:'});
        var durationInput = $('<input>', {
            type: 'text',
            class: 'form-control duration',
            readonly: true
        });

        // Return the parent element with the all the time elements appended 
        return timeDiv.append([start, startInput, end, endInput, duration, durationInput]);
    }
};


function HighlightLabels(wavesurfer, stages) {
    this.wavesurfer = wavesurfer;
    this.stages = stages;
    this.highlightLabelsDom = null;
    this.events = [];
}

HighlightLabels.prototype = {
    create: function () {
        var my = this;

        // Create the change button
        var highlightButton = $('<button/>', {
            text: 'Whistle',
            class: 'highlight_it btn',
        });
        highlightButton.click(function () {
            if (highlightButton.text() === 'Whistle') {
                for (var region_id in my.wavesurfer.regions.list) {
                    var event = my.wavesurfer.regions.list[region_id];
                    if (event.annotation === 'speech') {
                        $(event.element).addClass('current_region');
                        $(event.annotationLabel.element).addClass('current_label');
                    }

                }
                highlightButton.css("background-color", "green");
                highlightButton.text("dsds")
            } else {
                for (var region_id in my.wavesurfer.regions.list) {
                    var event = my.wavesurfer.regions.list[region_id];

                    $(event.element).removeClass('current_region');
                    $(event.annotationLabel.element).removeClass('current_label');

                    // $(event.element).removeClass('current_region');
                    // $(event.annotationLabel.element).removeClass('current_label');
                    // my.stages.updateStage(3, event);
                }
                highlightButton.css("background-color", "gray");
                highlightButton.text('Whistle')
            }


        });

        this.highlightLabelsDom = [highlightButton];
    },

    // Switch stages and the current region
    updateStage: function (newStage, region) {
        // Swap regions 
        this.swapRegion(newStage, region);

        // Update the dom of which ever stage the user is switching to
        var newContent = null;
        if (this.alwaysShowTags) {
            newContent = this.stageThreeView.dom;
        } else {
            if (newStage === 1) {
                this.stageOneView.update(null, null, this.wavesurfer.isPlaying());
                newContent = this.stageOneView.dom;
            } else if (newStage === 2) {
                this.stageTwoView.update(region);
                newContent = this.stageTwoView.dom;
            } else if (newStage === 3) {
                this.stageThreeView.update(region);
                newContent = this.stageThreeView.dom;
            }
        }


        if (newContent) {
            // Update current stage
            this.currentStage = newStage;

            // Detach the previous stage dom and append the updated stage dom to the stage container
            var container = $('.creation_stage_container');
            if (this.alwaysShowTags) {
                container.hide(10, function () {
                    container.children().detach();
                    container.append(newContent).show();
                });
            } else {
                container.fadeOut(10, function () {
                    container.children().detach();
                    container.append(newContent).fadeIn();
                });
            }
        }
        // Alert the user of a hint
        this.hint();
    },

    swapRegion: function (newStage, region) {
        if (this.currentRegion) {
            this.currentRegion.update({drag: false, resize: false});
            $(this.currentRegion.element).removeClass('current_region');
            $(this.currentRegion.annotationLabel.element).removeClass('current_label');

            // Remove the highlated label and disable.
            $('.annotation_tag', this.dom).removeClass('selected');
            $('.proximity_tag', this.dom).removeClass('selected');
            $('.annotation_tag', this.dom).addClass('disabled');
            $('.proximity_tag', this.dom).addClass('disabled');
        }

        // If the user is switch to stage 3, enable drag and resize editing for the new current region. 
        // Also highlight the label and region border
        if (region) {
            if (newStage === 2) {
                region.update({drag: false, resize: false});
            } else if (newStage === 3) {
                region.update({drag: true, resize: true});
                $(region.element).addClass('current_region');
                $(region.annotationLabel.element).addClass('current_label');
            }
        }
        this.currentRegion = region;
    },


    update: function () {
        $(this.highlightLabelsDom).detach();
        $('.highlight_labels').append(this.highlightLabelsDom);
        this.events = [];
    },

    getEvents: function () {
        // Return shallow copy
        return this.events.slice();
    },
}

/*
used for undo redo buttons
*/

function UndoRedo(wavesurfer) {
    this.wavesurfer = wavesurfer;
    this.changeViewDom = null;
    this.events = [];
}

UndoRedo.prototype = {
    create: function () {
        var my = this;

        // Create the undo button
        var undoButton = $('<button/>', {
            text: 'Undo',
            class: 'btn submit',
            style: "text-transform:uppercase !important;"
        });


        // Create the redo button
        var redoButton = $('<button/>', {
            text: 'Redo',
            class: 'btn submit',
            style: "text-transform:uppercase !important;"
        });

        this.changeViewDom = [undoButton, redoButton];
    }
}

/*
used for changing the view of the spectogram
*/

function ChangeView(wavesurfer) {
    this.wavesurfer = wavesurfer;
    this.changeViewDom = null;
    this.events = [];
}

ChangeView.prototype = {
    create: function () {
        var my = this;

        // Create the change button
        var changeButton = $('<button/>', {
            text: 'Spectrogram',
            class: 'view_type btn submit',
            style: "text-transform:uppercase !important;"
        });
        changeButton.click(function () {
            my.trackEvent('click-' + ((my.wavesurfer.params.visualization === 'spectrogram') ? 'waveform' : 'spectrogram'));
        });

        this.changeViewDom = [changeButton];
    },

    trackEvent: function (eventString) {
        console.log(eventString)
        var my = this;
        var visualization = this.wavesurfer.params.visualization;
        if (visualization === "spectrogram") {

            my.wavesurfer.drawer.clearWave();
            my.wavesurfer.empty()
            my.wavesurfer.params.visualization = "waveform"
            my.wavesurfer.drawBuffer();
            // this.wavesurfer.load("/static/wav/spectrogram_demo_doorknock_mono.wav");
            $(".view_type").html('spectrogram');
        }

        if (visualization === "waveform") {

            my.wavesurfer.drawer.clearWave();
            my.wavesurfer.empty()
            my.wavesurfer.params.visualization = "spectrogram"
            my.wavesurfer.drawBuffer();
            // this.wavesurfer.load("/static/wav/spectrogram_demo_doorknock_mono.wav");
            $(".view_type").html('waveform');
            console.log(my.wavesurfer.params)
        }

        var request = $.ajax({
            url: "/saveTelemetry",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                action: eventString,
                annotation_type: 'fg',
                task_id: task_id,
                batch_number: batch_number,
            }),
        })
        var eventData = {
            event: eventString,
            visualization: visualization
        };

        this.events.push(eventData);
    },


    update: function () {
        $(this.changeViewDom).detach();
        $('.change_view').append(this.changeViewDom);
        this.events = [];
    },

    getEvents: function () {
        // Return shallow copy
        return this.events.slice();
    },
}


function ZoomSize(wavesurfer) { // name should have been spectogram!!
    this.wavesurfer = wavesurfer;
    this.changeViewDom = null;
    this.events = [];
}

ZoomSize.prototype = {
    create: function () {
        var my = this;

        var change_view = $('<span>', {
            class: "change_view",
        })

        $('.zoom_size').append(change_view);

        this.changeViewDom = [change_view];
    },

    update: function () {
        // $(this.changeViewDom).detach();
        this.events = [];
    },

    getEvents: function () {
        // Return shallow copy
        return this.events.slice();
    },
};

/*
 * Purpose:
 *   Used for the play button and timestamp that controls how the wavesurfer audio is played
 * Dependencies:
 *   jQuery, Font Awesome, Wavesurfer (lib/wavesurfer.min.js), Util (src/components.js), audio-annotator.css
 */

function PlayBar(wavesurfer) {
    this.wavesurfer = wavesurfer;
    // Dom element containing play button and progress timestamp
    this.playBarDom = null;
    // List of user actions (click-pause, click-play, spacebar-pause, spacebar-play) with
    // timestamps of when the user took the action
    this.events = [];
}

PlayBar.prototype = {

    // Return a string of the form "<current_time> / <clip_duration>" (Ex "00:03.644 / 00:10.796")
    getTimerText: function () {
        return Util.secondsToString(this.wavesurfer.getCurrentTime()) +
            ' / ' + Util.secondsToString(this.wavesurfer.getDuration());
    },

    // Create the play bar and progress timestamp html elements and append eventhandlers for updating
    // these elements for when the clip is played and paused
    create: function () {
        var my = this;
        this.addWaveSurferEvents();

        // Create the play button
        var playButton = $('<i>', {
            class: 'play_audio fa fa-play-circle',
        });
        playButton.click(function () {
            my.trackEvent('click-' + (my.wavesurfer.isPlaying() ? 'pause' : 'play'));
            my.wavesurfer.playPause();
        });

        // Create audio timer text
        var timer = $('<span>', {
            class: 'timer',
        });

        this.playBarDom = [playButton, timer];
    },

    // Append the play buttom and the progress timestamp to the .play_bar container
    update: function () {
        $(this.playBarDom).detach();
        $('.play_bar').append(this.playBarDom);
        this.events = [];
        this.updateTimer();
    },

    // Update the progress timestamp (called when audio is playing)
    updateTimer: function () {
        $('.timer').text(this.getTimerText());
    },

    // Used to track events related to playing and pausing the clip (click or spacebar)
    trackEvent: function (eventString) {
        var audioSourceTime = this.wavesurfer.getCurrentTime();

        var eventData = {
            event: eventString,
            time: new Date().getTime(),
            audioSourceTime: audioSourceTime
        };
        var request = $.ajax({
            url: "/saveTelemetry",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                action: eventString,
                annotation_type: 'fg',
                task_id: task_id,
                batch_number: batch_number,
                extra_info: audioSourceTime
            }),
        })
        this.events.push(eventData);
    },

    // Return the list of events representing the actions the user did related to playing and
    // pausing the audio
    getEvents: function () {
        // Return shallow copy
        return this.events.slice();
    },

    // Add wavesurfer event handlers to update the play button and progress timestamp
    addWaveSurferEvents: function () {
        var my = this;

        this.wavesurfer.on('play', function () {
            $('.play_audio').removeClass('fa-play-circle').addClass('fa-stop-circle');
        });

        this.wavesurfer.on('pause', function () {
            $('.play_audio').removeClass('fa-stop-circle').addClass('fa-play-circle');
        });

        this.wavesurfer.on('seek', function () {
            my.updateTimer();
        });

        this.wavesurfer.on('audioprocess', function () {
            my.updateTimer();
        });

        // Play and pause on spacebar keydown
        $(document).on("keydown", function (event) {
            if (event.keyCode === 32) {
                if ($('.modal').is(':visible') == false) {
                    console.log(my.wavesurfer.regions)
                    event.preventDefault();
                    my.trackEvent('spacebar-' + (my.wavesurfer.isPlaying() ? 'pause' : 'play'));
                    my.wavesurfer.playPause();
                }

            }
        });
    },
};

/*
 * Purpose:
 *   Used for the workflow buttons that are used to submit annotations or to exit the task
 * Dependencies:
 *   jQuery, audio-annotator.css
 */

function WorkflowBtns(exitUrl) {
    // Dom of submit and load next btn
    this.nextBtn = null;
    // Dom of exit task btn
    this.exitBtn = null;
    // Dom of flag file btn
    this.flagBtn = null;

    // this.loadingbtn = null;

    // The url the user will be directed to when they exit
    this.exitUrl = exitUrl;

    // Boolean that determined if the exit button is shown
    this.showExitBtn = false;
}

WorkflowBtns.prototype = {
    // Create dom elements for the next and exit btns
    create: function () {
        var my = this;

        this.flagBtn = $('<a>', {
            href: "#modal_flag",
            type: 'button',
            class: 'btn flag modal-trigger red accent-4',
            text: 'FLAG FILE',


        });

        $('#ok').click(function () {
            $(my).trigger('flag-file');
        });

        // this.flagBtn.click(function(){
        //     $('#modal_flag').modal('open');
        // })

        this.nextBtn = $('<button>', {
            id: 'submit_annotation',
            class: 'btn submit indigo darken-4',
            text: 'SUBMIT & LOAD NEXT RECORDING'
        });
        this.nextBtn.click(function () {
            $(my).trigger('submit-annotations');
        });

        this.exitBtn = $('<button>', {
            text: 'Exit Now',
            class: 'exit btn',
        });
        this.exitBtn.click(function () {
            window.location = my.exitUrl;
        });

        // this.loadingbtn = $('<p>'),{
        //     id: "loading",
        //     text: "Loading Next File",
        //     img: '/static/img/loading.gif'
        // }


    },

    // Append the next and exit elements to the the parent container
    update: function () {
        $('.submit_container').append(this.flagBtn);
        $('.submit_container').append(this.nextBtn);
        // $('.submit_container').append(this.loadingbtn);
        if (this.showExitBtn) {
            $('.submit_container').append(this.exitBtn);
        }
    },

    // Set the value of showExitBtn
    setExitBtnFlag: function (showExitBtn) {
        this.showExitBtn = showExitBtn;
    }
};
