'use strict';

/*
 * Purpose:
 *   Combines all the components of the interface. Creates each component, gets task
 *   data, updates components. When the user submits their work this class gets the workers
 *   annotations and other data and submits to the backend
 * Dependencies:
 *   AnnotationStages (src/annotation_stages.js), PlayBar & WorkflowBtns (src/components.js), 
 *   HiddenImg (src/hidden_image.js), colormap (colormap/colormap.min.js) , Wavesurfer (lib/wavesurfer.min.js)
 * Globals variable from other files:
 *   colormap.min.js:
 *       magma // color scheme array that maps 0 - 255 to rgb values
 *    
 */

function Annotator() {
    this.wavesurfer;
    this.playBar;
    this.stages;
    this.workflowBtns;
    this.currentTask;
    this.taskStartTime;
    this.hiddenImage;
    // only automatically open instructions modal when first loaded
    this.instructionsViewed = false;
    // Boolean, true if currently sending http post request 
    this.sendingResponse = false;
    this.changeView;
    this.zoomSize;
    this.highlightLabels;
    // change color pallet from here
    // this.color_pallet = ['#3a86ff', '#ff006e', '#8338ec', '#fb5607', '#ffbe0b', '#06d6a0'];
    this.color_pallet = {
        'Speech': '#003f88',
        'TV': '#ff006e',
        'Crowd': '#8338ec',
        'Noise': '#fb5607',
        'Unintelligible': '#b6ccfe',
        'Singing': '#ffe6a7',
        'Person_B': '#5f0f40',
        'Person_C': '#fb8b24',
        'Others': '#0f4c5c',
    }

    // Create color map for spectrogram
    var spectrogramColorMap = colormap({
        colormap: 'jet',
        nshades: 256,
        format: 'rgb',
        alpha: 1,
    });

    // Create wavesurfer (audio visualization component)
    var height = 256;
    this.wavesurfer = Object.create(WaveSurfer);
    this.wavesurfer.init({
        container: '.audio_visual',
        waveColor: '#46494c',
        progressColor: '#000080',
        responsive: 1,
        scrollWidth: 0,
        hideScrollbar: true,

        fillParent: true,
        scrollParent: false,
        sampleRate: 16000,
        // backend: 'AudioElement',
        // barWidth: 1,
        // For the spectrogram the height is half the number of fftSamples
        fftSamples: height * 2,
        height: height,
        colorMap: spectrogramColorMap,

    });

    console.log(this.wavesurfer)

    // Create the play button and time that appear below the wavesurfer
    this.playBar = new PlayBar(this.wavesurfer);
    this.playBar.create();

    //create the change view vutton 
    this.changeView = new ChangeView(this.wavesurfer);
    this.changeView.create();

    this.zoomSize = new ZoomSize(this.wavesurfer);
    this.zoomSize.create();
    // this.index_history = null

    // Create the annotation stages that appear below the wavesurfer. The stages contain tags 
    // the users use to label a region in the audio clip
    this.stages = new AnnotationStages(this.wavesurfer);
    this.stages.create();

    this.highlightLabels = new HighlightLabels(this.wavesurfer, this.stages);
    this.highlightLabels.create();

    // Create Workflow btns (submit and exit)
    this.workflowBtns = new WorkflowBtns();
    this.workflowBtns.create();


    this.addEvents();
}

Annotator.prototype = {
    addWaveSurferEvents: function () {
        var my = this;

        // function that moves the vertical progress bar to the current time in the audio clip
        var updateProgressBar = function () {
            var progress = my.wavesurfer.getCurrentTime() / my.wavesurfer.getDuration();
            my.wavesurfer.seekTo(progress);
        };

        // Update vertical progress bar to the currentTime when the sound clip is 
        // finished or paused since it is only updated on audioprocess
        this.wavesurfer.on('pause', updateProgressBar);
        this.wavesurfer.on('finish', updateProgressBar);

        // When a new sound file is loaded into the wavesurfer update the  play bar, update the 
        // annotation stages back to stage 1, update when the user started the task, update the workflow buttons.
        this.wavesurfer.on('ready', function () {
            my.playBar.update();
            my.changeView.update();
            my.zoomSize.update();
            my.highlightLabels.update();
            my.stages.updateStage(1);
            my.updateTaskTime();
            my.workflowBtns.update();
        });

        this.wavesurfer.on('click', function (e) {
            my.stages.clickDeselectCurrentRegion();
        });

    },

    updateTaskTime: function () {
        this.taskStartTime = new Date().getTime();
    },

    // Event Handler, if the user clicks submit annotations call submitAnnotations
    addWorkflowBtnEvents: function () {
        $(this.workflowBtns).on('submit-annotations', this.submitAnnotations.bind(this));
        $(this.workflowBtns).on('flag-file', this.flagFile.bind(this));
    },

    addEvents: function () {
        this.addWaveSurferEvents();
        this.addWorkflowBtnEvents();
    },

    // Update the task specific data of the interfaces components
    update: function (prev = false) {
        console.log("pass_id", pass_id)
        console.log("speech_annotations", speech_annotations)
        var my = this;
        // $(my.workflowBtns).on('flag-file', my.flagFile.bind(my));
        my.wavesurfer.empty()
        my.wavesurfer.un('ready')
        // my.wavesurfer.destroy();

        // Update the different tags the user can use to annotate, also update the solutions to the
        // annotation task if the user is suppose to recieve feedback
        var annotationTags = my.currentTask.annotationTag;
        var tutorialVideoURL = my.currentTask.tutorialVideoURL;

        var instructions = my.currentTask.instructions;
        my.stages.updateStage(1);
        my.stages.reset(
            annotationTags, pass_id
        );

        var labels = Object.create(WaveSurfer.Labels);
        labels.init({
            wavesurfer: my.wavesurfer,
            container: '.labels0',
            label_container: annotationTags[0],
            color_pallet: my.color_pallet,
            height: "50",
            annotation_labels: annotationTags,
            pass_id: pass_id,
            speech_annotations: speech_annotations
        });
        if (pass_id === '3') {
            console.log("pass id is 3")
        }
        // addEventsHighlighter
        $("#radio0").prop("checked", true);
        var title = ''
        annotationTags.forEach(function (tagName, index) {
            title += tagName + ','
            $("#radio" + index).click(function () {
                if ($(this).is(':checked')) {
                    // my.stages.currentRegion.update({drag: false, resize: false});
                    labels.change_container(".labels" + index, tagName, "." + tagName)
                }

            });

            $("#annotation" + index).on({
                mouseenter: function () {
                    for (var region_id in my.wavesurfer.regions.list) {
                        var event = my.wavesurfer.regions.list[region_id];
                        if (event.annotation === tagName) {
                            $(event.element).addClass('current_region');
                            $(event.annotationLabel.element).addClass('current_label');
                        }
                    }
                },
                mouseleave: function () {
                    for (var region_id in my.wavesurfer.regions.list) {
                        var event = my.wavesurfer.regions.list[region_id];
                        $(event.element).removeClass('current_region');
                        $(event.annotationLabel.element).removeClass('current_label');
                    }
                },
            });

            $("#checkbox" + index).click(function () {
                if (this.checked) {
                    for (var region_id in my.wavesurfer.regions.list) {
                        var event = my.wavesurfer.regions.list[region_id];
                        if (event.annotation === tagName) {

                            $(event.element).css({
                                "background-color": my.color_pallet[tagName],
                                "opacity": 0.5,
                            });
                        }
                    }
                } else {
                    for (var region_id in my.wavesurfer.regions.list) {
                        var event = my.wavesurfer.regions.list[region_id];
                        if (event.annotation === tagName) {
                            $(event.element).css({
                                "background-color": ""
                            });
                        }
                    }
                }

            })

        })
        $('#title').html('<b><code>' + title.substring(0, title.length - 1) + '</code></b>' + '&nbsp; pass')

        $("#undobtn").unbind();
        $("#redobtn").unbind();

        $('#undobtn').click(function () {
            var undo_stack = my.stages.getUndoStack()
            var redo_stack = my.stages.getRedoStack()

            if (undo_stack[undo_stack.length - 1].event === 'create') {
                var annotation = undo_stack[undo_stack.length - 1].annotation
                var start = undo_stack[undo_stack.length - 1].start
                var end = undo_stack[undo_stack.length - 1].end
                var id = undo_stack[undo_stack.length - 1].id
                my.stages.flag_performing_undo_or_redo = true
                my.wavesurfer.regions.list[id].remove()
                my.stages.flag_performing_undo_or_redo = false

            } else if (undo_stack[undo_stack.length - 1].event === 'delete') {
                var annotation = undo_stack[undo_stack.length - 1].annotation
                var start = undo_stack[undo_stack.length - 1].start
                var end = undo_stack[undo_stack.length - 1].end
                var id = undo_stack[undo_stack.length - 1].id

                // save current container index
                my.stages.flag_performing_undo_or_redo = true
                var current_container_index = labels.container.className[labels.container.className.length - 1]
                labels.change_container(".labels" + annotationTags.indexOf(annotation), annotation, "." + annotation)
                my.stages.createAnnotationWithId(id, start, end)
                labels.change_container(".labels" + current_container_index, annotationTags[current_container_index], "." + annotationTags[current_container_index])
                my.stages.flag_performing_undo_or_redo = false
            } else {
                var annotation = undo_stack[undo_stack.length - 1].annotation
                var start = undo_stack[undo_stack.length - 1].start
                var end = undo_stack[undo_stack.length - 1].end
                var id = undo_stack[undo_stack.length - 1].id

                // check the previous event ( its either create or drag or resize)
                for (var i = undo_stack.length - 2; i >= 0; i--) {
                    if (undo_stack[i].id === id) {

                        my.stages.flag_performing_undo_or_redo = true
                        my.wavesurfer.regions.list[id].start = undo_stack[i].start
                        my.wavesurfer.regions.list[id].end = undo_stack[i].end
                        var data = {'annotation': annotation, 'start': undo_stack[i].start, 'end': undo_stack[i].end}
                        my.wavesurfer.regions.list[id].update(data)
                        my.stages.flag_performing_undo_or_redo = false
                        break;
                    }
                }

            }
            var popped_event = undo_stack.pop()
            redo_stack.push(popped_event)
            my.stages.updateUndoStack(undo_stack)
            my.stages.updateRedoStack(redo_stack)
            document.querySelector('#redobtn').removeAttribute('disabled');
            if (undo_stack.length == 0) {
                $("#undobtn").attr("disabled", "disabled");
            }
            var request = $.ajax({
                url: "/saveTelemetry",
                type: "POST",
                contentType: "application/json",
                data: JSON.stringify({
                    action: 'undo',
                    annotation_type: 'fg',
                    task_id: task_id,
                    batch_number: batch_number
                }),
            })
        });

        $('#redobtn').click(function () {
            var redo_stack = my.stages.getRedoStack()
            var undo_stack = my.stages.getUndoStack()
            if (redo_stack[redo_stack.length - 1].event === 'create') {
                var annotation = redo_stack[redo_stack.length - 1].annotation
                var start = redo_stack[redo_stack.length - 1].start
                var end = redo_stack[redo_stack.length - 1].end
                var id = redo_stack[redo_stack.length - 1].id
                var current_container_index = labels.container.className[labels.container.className.length - 1]

                my.stages.flag_performing_undo_or_redo = true
                labels.change_container(".labels" + annotationTags.indexOf(annotation), annotation, "." + annotation)
                my.stages.createAnnotationWithId(id, start, end)
                labels.change_container(".labels" + current_container_index, annotationTags[current_container_index], "." + annotationTags[current_container_index])
                my.stages.flag_performing_undo_or_redo = false

            } else if (redo_stack[redo_stack.length - 1].event === 'delete') {
                var annotation = redo_stack[redo_stack.length - 1].annotation
                var start = redo_stack[redo_stack.length - 1].start
                var end = redo_stack[redo_stack.length - 1].end
                var id = redo_stack[redo_stack.length - 1].id

                my.stages.flag_performing_undo_or_redo = true
                my.wavesurfer.regions.list[id].remove()
                my.stages.flag_performing_undo_or_redo = false

            } else {
                var annotation = redo_stack[redo_stack.length - 1].annotation
                var start = redo_stack[redo_stack.length - 1].start
                var end = redo_stack[redo_stack.length - 1].end
                var id = redo_stack[redo_stack.length - 1].id

                my.stages.flag_performing_undo_or_redo = true
                my.wavesurfer.regions.list[id].start = start
                my.wavesurfer.regions.list[id].end = end
                var data = {'annotation': annotation, 'start': start, 'end': end}
                my.wavesurfer.regions.list[id].update(data)
                my.stages.flag_performing_undo_or_redo = false

            }

            var popped_event = redo_stack.pop()
            undo_stack.push(popped_event)
            my.stages.updateUndoStack(undo_stack)
            my.stages.updateRedoStack(redo_stack)
            document.querySelector('#undobtn').removeAttribute('disabled');
            if (redo_stack.length == 0) {
                $("#redobtn").attr("disabled", "disabled");
            }

            var request = $.ajax({
                url: "/saveTelemetry",
                type: "POST",
                contentType: "application/json",
                data: JSON.stringify({
                    action: 'redo',
                    annotation_type: 'fg',
                    task_id: task_id,
                    batch_number: batch_number
                }),
            })

        });


        // set video url
        $('#tutorial-video').attr('src', tutorialVideoURL);

        // add instructions
        var instructionsContainer = $('#instructions-container');
        instructionsContainer.empty();
        if (typeof instructions !== "undefined") {
            $('.modal-trigger').leanModal();
            instructions.forEach(function (instruction, index) {
                if (index == 0) {
                    // first instruction is the header
                    var instr = $('<h4>', {
                        html: instruction
                    });
                } else {
                    var instr = $('<h6>', {
                        "class": "instruction",
                        html: instruction
                    });
                }
                instructionsContainer.append(instr);
            });

        } else {
            $('#instructions-container').hide();
            $('#trigger').hide();
        }

        // Update the visualization type and the feedback type and load in the new audio clip
        my.wavesurfer.params.visualization = my.currentTask.visualization; // invisible, spectrogram, waveform
        my.wavesurfer.load("/getFile?patient_name=" + patient_name + "&audiofile_id=" + audiofile_id + "&cgsegment_id=" + cgsegment_id)


        this.wavesurfer.on('ready', function () {
            my.playBar.update();
            my.changeView.update();
            my.zoomSize.update();
            my.highlightLabels.update();
            my.stages.updateStage(1);
            my.updateTaskTime();
            my.workflowBtns.update();


            $.get(
                "/fineGrainedAnnotation/getAnnotations?batch_number=" + batch_number + "&num_in_batch=" + num_in_batch,
                function (annotations) {
                    if (typeof data === 'string') {
                        $('#no_annotation').attr('style', 'display:block');
                        $('.annotation').attr('style', 'display:none');
                    } else {

                        my.stages.clear()

                        if (pass_id === '3') {
                            // my.stages.clear()
                            for (var lbl in speech_annotations) {
                                labels.change_container(".labels00", lbl, "." + lbl)
                                for (var s_e in speech_annotations[lbl]) {
                                    my.stages.createspeechAnnotation(speech_annotations[lbl][s_e].start, speech_annotations[lbl][s_e].end)

                                }
                            }
                        }

                        for (var lbl in annotations) {
                            labels.change_container(".labels" + annotationTags.indexOf(lbl), lbl, "." + lbl)
                            for (var s_e in annotations[lbl]) {
                                my.stages.createAnnotation(annotations[lbl][s_e].start, annotations[lbl][s_e].end)

                                // console.log(my.stages.wavesurfer.regions.list(annotations[]))
                            }

                        }
                        labels.change_container(".labels0", annotationTags[0], "." + annotationTags[0])

                        // removing the selected property of regions
                        for (var region_id in my.wavesurfer.regions.list) {
                            var event = my.wavesurfer.regions.list[region_id];
                            $(event.element).removeClass('current_region');
                            $(event.annotationLabel.element).removeClass('current_label');
                        }


                    }
                }
            );
        })


        $('.tooltipped').tooltip();
        // $('.modal').modal();

    },

    load_next_file_info: function (current_pass) {
        $('#loading').attr('style', 'display:block');
        $("#submit_annotation").attr("disabled", "disabled");
        $(".flag").attr("disabled", "disabled");
        var my = this;
        $.get(
            "fineGrainedAnnotation/getNextFileInfo/",
            function (data) {
                if (typeof data === 'string') {
                    $('#no_annotation').attr('style', 'display:inline-block;');
                    $("#no_annotation").html(data);
                    $('.annotation').attr('style', 'display:none');
                    $('#last_task').hide();
                    $('#loading').attr('style', 'display:none');
                } else {
                    var dataUrl = {
                        "visualization": data.visualization,
                        "annotationTag": data.annotationTag,
                        "instructions": data.instructions
                    }
                    latest = data.num_in_batch - 1;
                    batch_id = data.batch_id;
                    task_id = data.task_id;
                    num_in_batch = data.num_in_batch
                    batch_size = data.batch_size
                    batch_number = data.batch_number
                    cgsegment_id = data.cgsegment_id
                    audiofile_id = data.audiofile_id
                    patient_name = data.patient_name
                    popup = data.popup;
                    previous_labels_so_far = data.previous_labels_so_far;
                    pass_id = data.pass_id;
                    speech_annotations = data.speech_annotations;
                    $('input[type="range"]').rangeslider();

                    // Load the next audio annotation task
                    console.log(current_pass !== undefined)


                    my.loadTask(dataUrl);
                
                    my.instructionsViewed = popup
                    
                    if (my.instructionsViewed) {
                        console.log("showd")
                        $('#instructions-modal').openModal();
                        
                    }
                   
                    document.getElementById("description").value = '';
                    $("#last_task").hide();
                    $('#no_annotation').hide();
                    $('.annotation').attr('style', 'display:block');
                    $("#instructionsbtn").attr('style', 'display:block');
                    $("#file_number").html("File " + (num_in_batch) + "/" + batch_size + ' id:' + batch_id + ' task_id:' + task_id + ", batch_number:" + batch_number);
                    document.querySelector("#submit_annotation").removeAttribute('disabled');
                    load_steps(false, my.load_previous_file_info, previous_labels_so_far, my)
                    document.querySelector("#submit_annotation").removeAttribute('disabled');
                    document.querySelector(".flag").removeAttribute('disabled');
                    $('#loading').attr('style', 'display:none');
                }

            }
        );
    },

    load_previous_file_info: function (num_in_batch_requested, my) {
        $('#loading').attr('style', 'display:block');
        $("#submit_annotation").attr("disabled", "disabled");
        $(".flag").attr("disabled", "disabled");
        // var my = this;
        $.get(
            "fineGrainedAnnotation/getPreviousFileInfo/?batch_number=" + batch_number + "&num_in_batch=" + num_in_batch_requested + "&current_task=" + task_id,
            function (data) {
                if (typeof data === 'string') {
                    alert("Sorry you cannot go to this task!")
                } else {
                    var dataUrl = {
                        "visualization": data.visualization,
                        "annotationTag": data.annotationTag,
                        "instructions": data.instructions
                    }
                    latest = data.latest
                    batch_id = data.batch_id
                    task_id = data.task_id
                    num_in_batch = data.num_in_batch
                    batch_size = data.batch_size
                    batch_number = data.batch_number
                    cgsegment_id = data.cgsegment_id
                    audiofile_id = data.audiofile_id
                    patient_name = data.patient_name
                    previous_labels_so_far = data.previous_labels_so_far;
                    pass_id = data.pass_id;
                    speech_annotations = data.speech_annotations;
                    document.getElementById("description").value = data.description
                    $('input[type="range"]').rangeslider();
                    // var annotator = new Annotator();
                    // Load the previous audio annotation task
                    my.loadTask(dataUrl);
                    $("#last_task").hide();
                    $('#no_annotation').hide();
                    $('.annotation').attr('style', 'display:block');
                    $("#instructionsbtn").attr('style', 'display:block');
                    $("#file_number").html("File " + (num_in_batch) + "/" + batch_size + ' batch_id:' + batch_id + ' task_id:' + task_id + ", batch_number:" + batch_number);
                    load_steps(false, my.load_previous_file_info, previous_labels_so_far, my)
                    // my.load_steps(false, my.load_previous_file_info, previous_labels_so_far, my)
                    document.querySelector("#submit_annotation").removeAttribute('disabled');
                    document.querySelector(".flag").removeAttribute('disabled');
                    $('#loading').attr('style', 'display:none');

                }
            }
        );
    },


    // Update the interface with the next task's data
    loadTask: function (dataUrl) {
        this.currentTask = dataUrl;
        this.update();
    },

    flagFile: function () {
        var my = this;
        if (this.sendingResponse) {
            // If it is already sending a post with the data, do nothing
            return;
        }
        this.sendingResponse = true;

        $.ajax({
            url: "/fineGrainedAnnotation/flagFile",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                description: document.getElementById('description').value,
                batch_id: batch_id,
                num_in_batch: num_in_batch,
                batch_number: batch_number
            }),
            success: function (data) {
                if (data.msg === 'last_task') {
                    show_batch_end(my);
                    latest = num_in_batch + 1;
                    previous_labels_so_far = data.previous_labels_so_far;
                    load_steps(true, my.load_previous_file_info, previous_labels_so_far, my)
                    // my.load_steps(true, my.load_previous_file_info, previous_labels_so_far, my);
                } else if (data.msg !== 'success') {
                    show_end_or_error(data.msg); // todo
                } else {
                    $("#confirmation").attr('style', 'display:block'); // change its location
                    setTimeout(function () {
                        $("#confirmation").attr('style', 'display:none')
                    }, 2000);
                    my.load_next_file_info();
                }
            }
        })
            .always(function () {
                // No longer sending response
                my.sendingResponse = false;
            });
    },


    // Collect data about users annotations and submit it to the backend
    submitAnnotations: function () {
        var my = this;
        // Check if all the regions have been labeled before submitting
        // if (this.stages.annotationDataValidationCheck()) {
        if (this.sendingResponse) {
            // If it is already sending a post with the data, do nothing
            return;
        }
        this.sendingResponse = true;
        // Get data about the annotations the user has created
        var content = {
            task_start_time: this.taskStartTime,
            task_end_time: new Date().getTime(),
            batch_id: batch_id,
            num_in_batch: num_in_batch,
            batch_number: batch_number,
            visualization: this.wavesurfer.params.visualization,
            annotations: this.stages.getAnnotations(pass_id),
            deleted_annotations: this.stages.getDeletedAnnotations(),
            // List of the different types of actions they took to create the annotations
            annotation_events: this.stages.getEvents(),
            // List of actions the user took to play and pause the audio
            play_events: this.playBar.getEvents(),
        };

        this.post(content);
        // }
    },


    // Make POST request, passing back the content data. On success load in the next task
    post: function (content) {
        // $('#loading').attr('style', 'display:block');
        // console.log("displajfkdjf")
        var my = this;
        $.ajax({
            url: "/fineGrainedAnnotation/submitAnnotation",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify(content),

            success: function (data) {
                if (data.msg === 'last_task') {
                    $("#confirmation").attr('style', 'display:block'); // change its location
                    setTimeout(function () {
                        $("#confirmation").attr('style', 'display:none')
                    }, 2000);
                    show_batch_end(my)
                    previous_labels_so_far = data.previous_labels_so_far;
                    load_steps(true, my.load_previous_file_info, previous_labels_so_far, my)
                    $('#loading').attr('style', 'display:none');
                } else if (data.msg !== 'success') {
                    $("#no_annotation").html(data);
                    $('#last_task').hide();
                    $('#loading').attr('style', 'display:none');
                } else {
                    $("#confirmation").attr('style', 'display:block'); // change its location
                    setTimeout(function () {
                        $("#confirmation").attr('style', 'display:none')
                    }, 2000);
                    my.load_next_file_info();

                }
            },

        });
        my.sendingResponse = false;

    }

};

$(document).ready(function () {
});