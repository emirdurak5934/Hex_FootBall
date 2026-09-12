console.log("MULTIPLAYER.JS YÜKLENDİ");


const socket = io();


socket.on("connect", function () {

    console.log(
        "SOCKET BAĞLANDI:",
        socket.id
    );

});


socket.on("connect_error", function (error) {

    console.error(
        "SOCKET BAĞLANTI HATASI:",
        error
    );

});


const createRoomButton =
    document.getElementById(
        "createRoomButton"
    );


const joinRoomButton =
    document.getElementById(
        "joinRoomButton"
    );


const roomCodeInput =
    document.getElementById(
        "roomCodeInput"
    );


const roomStatus =
    document.getElementById(
        "roomStatus"
    );


const roomWaitingScreen =
    document.getElementById(
        "roomWaitingScreen"
    );


const createdRoomCode =
    document.getElementById(
        "createdRoomCode"
    );


const waitingMessage =
    document.getElementById(
        "waitingMessage"
    );


const leaveRoomButton =
    document.getElementById(
        "leaveRoomButton"
    );


console.log(
    "ODA KUR BUTTON:",
    createRoomButton
);


