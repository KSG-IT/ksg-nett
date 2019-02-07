// global: Chart, moment
const measurementUrl = '/api/sensors/measurements/'

const temperatureCanvas = document.getElementById("temperatureCanvas")
const humidityCanvas = document.getElementById("humidityCanvas")
const soundCanvas = document.getElementById("soundCanvas")

const temperatureCtx = temperatureCanvas.getContext("2d")
const humidityCtx = humidityCanvas.getContext("2d")
const soundCtx = soundCanvas.getContext("2d")

const temperatureGradient = temperatureCtx.createLinearGradient(0, 0, 0, 600)
temperatureGradient.addColorStop(0, 'rgba(244, 66, 66, 1)')
temperatureGradient.addColorStop(0.5, 'rgba(255, 251, 186, 0.75)')
temperatureGradient.addColorStop(1, 'rgba(130, 232, 255, 0.25)')

const humidityGradient = humidityCtx.createLinearGradient(0, 0, 0, 600)
humidityGradient.addColorStop(0, 'rgba(7, 49, 99, 1)')
humidityGradient.addColorStop(1, 'rgba(130, 232, 255, 0.25)')

const soundGradient = soundCtx.createLinearGradient(0, 0, 0, 600)
soundGradient.addColorStop(0, 'rgba(244, 66, 66, 1)')
soundGradient.addColorStop(0.25, 'rgb(38, 38, 38)')
soundGradient.addColorStop(1, 'rgba(200, 200, 200, 0.25)')

const temperatureChart = new Chart(temperatureCtx, {
  type: "line",
  data: {
    datasets: [{
      backgroundColor: temperatureGradient,
      label: "Temperature"
    }]
  },
  options: {
    scales: {
      yAxes: [{
        ticks: {
          callback: function(value, index, values) {
              return value + " °C";
          }
        }
      }]
    },
    tooltips: {
      callbacks: {
        label: function(tooltipItem, data){
          return "Temperature: " + tooltipItem.yLabel.toFixed(2) + " °C"
        }
      }
    }
  }
})
const humidityChart = new Chart(humidityCtx, {
  type: "line",
  data: {
    datasets: [{
      backgroundColor: humidityGradient,
      label: "Humidity"
    }]
  },
  options: {
    scales: {
      yAxes: [{
        ticks: {
          callback: function(value, index, values) {
            return value + "%";
          }
        }
      }]
    },
    tooltips: {
      callbacks: {
        label: function(tooltipItem, data){
          return "Humidity: " + tooltipItem.yLabel.toFixed(2) + "%"
        }
      }
    }
  }
})
const soundChart = new Chart(soundCtx, {
  type: "line",
  data: {
    datasets: [{
      backgroundColor: soundGradient,
      label: "Sound"
    }]
  },
  options: {
    scales: {
      yAxes: [{
        ticks: {
          callback: function(value, index, values) {
            return value + " dB";
          }
        }
      }]
    },
    tooltips: {
      callbacks: {
        label: function(tooltipItem, data){
          return "Volume: " + tooltipItem.yLabel.toFixed(2) + " dB"
        }
      }
    }
  }
})

function getTemperatureData(){
  return fetch(measurementUrl + `?type=temperature`)
    .then(response => response.json())
    .then(jsonData => {
      const dataValues = jsonData.map(x => x.value)
      const dataLabels = jsonData.map(x => moment(x.created_at).format("HH:mm"))
      temperatureChart.data.labels = dataLabels
      temperatureChart.data.datasets[0].data = dataValues
      temperatureChart.update()
    })
}

function getHumidityData(){
  return fetch(measurementUrl + `?type=humidity`)
    .then(response => response.json())
    .then(jsonData => {
      const dataValues = jsonData.map(x => x.value)
      const dataLabels = jsonData.map(x => moment(x.created_at).format("HH:mm"))
      humidityChart.data.labels = dataLabels
      humidityChart.data.datasets[0].data = dataValues
      humidityChart.update()
    })
}

function getSoundData(){
  return fetch(measurementUrl + `?type=sound`)
    .then(response => response.json())
    .then(jsonData => {
      const dataValues = jsonData.map(x => x.value)
      const dataLabels = jsonData.map(x => moment(x.created_at).format("HH:mm"))
      soundChart.data.labels = dataLabels
      soundChart.data.datasets[0].data = dataValues
      soundChart.update()
    })
}

getTemperatureData()
getHumidityData()
getSoundData()

setInterval(getTemperatureData, 60 * 1000)
setInterval(getHumidityData, 60 * 1000)
setInterval(getSoundData, 60 * 1000)
