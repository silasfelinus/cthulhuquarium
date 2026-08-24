//Virtual Aquarium
//By Silas Knight
//v0.01 Added bubbles


//random colors currently tweaked to give a tendency to blues
//future project could give random pallete
var sideWall = color(random(0,255),255,255);
var backWall = color(random(0,255),random(0,255),255);
var bottom = color(random(0,255),random(0,255),random(255));
var bubbles = [];
var fishFood = [];
var hungryFish = [];
var counter = 0;
var smallFish = 20;
var midFish = 4;
var bigFish = 2;
var smallSize = 1;
var midSize = 4;
var bigSize = 6;
var flag = "OK";

//Add fish to array
var makeFish = function(numberFish, sizeFish) {
    var fishes = [];
    for (var i = 0; i < numberFish; i++) {
        var colorBody = color(random(0,255), random(0, 255), random(1,255));
        var colorTail = color(random(0,255), random(0, 255), random(1,255));
        var bodyHeight = random(5,30)*sizeFish;
        var bodyWidth = random(5, 30)*sizeFish;
        var tailHeight = random(0.1, 0.6);
        var tailWidth = random(0.1, 0.7);
        var eyeSize = random(2, 5);
        var speed = random(0.01,1);
        var fishX = random(0,400);
        var fishY = random (0, 400);
        var directionX = 1;
        var directionY = 1;
        if (fishX > 200) {
            var directionX = -1;
        } 
        if (fishY > 200) {
            var directionY = -1;
        } 
        var fish = [fishX, fishY, directionX, directionY, colorBody, colorTail, bodyHeight, bodyWidth, tailHeight, tailWidth, eyeSize, speed];
        fishes.push(fish);
    }
    return fishes;
};
    





//Make a new bubble
var newBubble = function() {
    
    var bubbleSize =random(1, 10);
    var bubbleSpeed = floor(random(1, 3));
    var bubbleX = random(0,400);
    var bubble = [bubbleX, 400, bubbleSize, bubbleSpeed];
    return bubble;
};

var drawCastle = function() {
    var castleColor = color(230, 218, 85);
    fill(castleColor);
    var castleX = 200;
    var castleY = 250;
    var castleWidth = 150;
    var castleHeight = 70;
    //top
    rect(castleX+castleWidth*0.2, castleY*0.7, castleWidth*0.1, castleHeight*0.5);
    rect(castleX+castleWidth*0.45, castleY*0.71, castleWidth*0.1, castleHeight*0.5);
    rect(castleX+castleWidth*0.7, castleY*0.7, castleWidth*0.1, castleHeight*0.5);
    //middle
    rect(castleX+castleWidth*0.15, castleY*0.8, castleWidth*0.7, castleHeight*0.7);
    fill(0,0,0);
    ellipse(castleX+castleWidth*0.28, castleY*0.9, castleWidth*0.1, castleHeight*0.5);
    ellipse(castleX+castleWidth*0.5, castleY*0.9, castleWidth*0.1, castleHeight*0.5);
    ellipse(castleX+castleWidth*0.72, castleY*0.9, castleWidth*0.1, castleHeight*0.5);
    //bottom 
    fill(castleColor);
    rect(castleX, castleY, castleWidth, castleHeight);
    fill (0, 0, 0);
    ellipse(castleX+castleWidth/2, castleY*1.3, castleWidth*0.3, castleHeight*1.7);
    fill(bottom);
    noStroke();
    rect(castleX, castleY+castleHeight+1, castleWidth, castleHeight);
    stroke(1);
};



/*
fish = 
[0] = fishX
[1] = fishY
[2] = directionX
[3] = directionY
[4] = colorBody
[5] = colorTail
[6] = bodyHeight
[7] = bodyWidth
[8] = tailHeight
[9] = tailWidth
[10] = eyeSize
[11] = speed
*/

var drawFish = function(fish) {

    var bodyLength = fish[7];
    var bodyHeight = fish[6];
    var bodyColor = fish[4];
    var tailColor = fish[5];
    var eyeSize = fish[10];
    var speed = fish[11];
    var directionX = fish[2];
    var directionY = fish[3];
    
    //move
    var centerX = fish[0] + speed*directionX;
    var centerY = fish[1] + speed*directionY;

    fill(bodyColor);
    // body
    ellipse(centerX, centerY, bodyLength, bodyHeight);
    // tail
    fill(tailColor);
    
    //check for x direction and draw appropriately
    if (fish[2] === 1) {
    var tailWidth = bodyLength*fish[9];
    var tailHeight = bodyHeight*fish[8];
    triangle(centerX-bodyLength/2, centerY,
         centerX-bodyLength/2-tailWidth, centerY-tailHeight,
         centerX-bodyLength/2-tailWidth, centerY+tailHeight);
    // eye
    fill(33, 33, 33);
    ellipse(centerX+bodyLength/4, centerY, eyeSize, eyeSize);
    } else {
    var tailWidth = bodyLength*fish[9];
    var tailHeight = bodyHeight*fish[8];
    triangle(centerX+bodyLength/2, centerY,
         centerX+bodyLength/2+tailWidth, centerY-tailHeight,
         centerX+bodyLength/2+tailWidth, centerY+tailHeight);
    // eye
    fill(33, 33, 33);
    ellipse(centerX-bodyLength/4, centerY, eyeSize, eyeSize);
    }
};

var smallFishes = makeFish(smallFish, smallSize);
var midFishes = makeFish(midFish, midSize);
var bigFishes = makeFish(bigFish, bigSize);
var fishes = smallFishes.concat(midFishes, bigFishes);

mousePressed = function(){
    var newFood = [mouseX, mouseY];
    fishFood.push(newFood);
    hungryFish.push(floor(random(0,fishes.length)));
};

var handleFood = function() {
    for (var i = 0; i< fishFood.length; i++) {
        var tempFood = fishFood[i];
        tempFood[1] += 0.2;
        fill(220, 232, 127);
        rect(tempFood[0], tempFood[1], 5, 5);
        var fishIndex = hungryFish[i];
        var hector = fishes[fishIndex];
        hector[0] += hector[2]*3;
        hector[1] += hector[3]*3;
        if (hector[0] > tempFood[0]) {
            hector[2] = -1;
        }   else {
            hector[2] = 1;
        }
        if (hector[1] > tempFood[1]- 20) {
            hector[3] = -1;
        }   else {
            hector[3] = 1;
        }
    fishes[fishIndex] = hector;
    if (hector[0] - tempFood[0] < 20 && hector[0] - tempFood[0] > -20 &&
        hector[1] - tempFood[1] < 20 && hector[1] - tempFood[1] > -20) {
        fishFood.splice(i, 1); 
        hungryFish.splice(i, 1);
        flag = hungryFish[0];
        }
    }
};

draw = function() {
    counter++;
    
    //floor
    background(bottom);
    
    //sidewall
    fill(sideWall);
    triangle(0, 400, 0, 0, 260, 0);
    
    //backwall
    fill(backWall);
    var horizon = rect(65, 0, 400, 300);
    
    //castle
    drawCastle();
    
    //Adjust fish movement when they hit a wall
    for (var i = 0; i < fishes.length; i++) {
        var tempFish = fishes[i];
        
            tempFish[0] += tempFish[2]*tempFish[11];
            tempFish[1] += tempFish[3]*tempFish[11]/3;

        if (tempFish[0]>400) {
            tempFish[2] = -1;
        }
        if (tempFish[0]<0) {
            tempFish[2] = 1;
        }
        if (tempFish[1]<0) {
            tempFish[3] = 1;
        }
        if (tempFish[1]>400) {
            tempFish[3] = -1;
        }
        fishes[i] = tempFish;
        drawFish (fishes[i]);  
    }

    
    handleFood();
    
    //check if we need to make a new bubble and add to bubbles
    if (floor(random(0,20)) === 19) {
        var addBubble = newBubble();
        bubbles.push(addBubble);
    }


    //update bubbles
    //Bubble = [x, y, size, speed)
    var tempArray = [];
    
    for (var i = 0; i < bubbles.length; i++) {
        
        var currentBubble = bubbles[i];
        if (counter % currentBubble[3] === 0) {
            currentBubble[1] -= 1;
        }
        
        if (currentBubble[1] > 0) {
            tempArray.push(currentBubble);
            fill(135, 216, 230);
            stroke(3);
            ellipse (currentBubble[0], currentBubble[1], currentBubble[2], currentBubble[2]);
        }
    }
    bubbles = tempArray;


};

