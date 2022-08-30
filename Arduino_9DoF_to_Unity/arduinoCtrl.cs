// SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

using System.Collections;
using System.Collections.Generic;
using System.IO.Ports;
using UnityEngine;
using UnityEngine.UI;

public class arduinoCtrl : MonoBehaviour
{
    SerialPort stream = new SerialPort("COM52", 9600);
    //public float sensitivity;

    public Transform t;

    private float posX;
    private float posY;
    private float posZ;

    private float sensX;
    private float sensY;
    private float sensZ;

    public float Xcal;
    public float Ycal;
    public float Zcal;

    void Start()
    {
        stream.Open();
        //stream.ReadTimeout = 20;
    }

    void Update()
    {
        Vector3 lastData = Vector3.zero;

        string UnSplitData = stream.ReadLine();
        print(UnSplitData);
        string[] SplitData = UnSplitData.Split('|');

        float AccX = float.Parse(SplitData[1]);
        float AccY = float.Parse(SplitData[2]);
        float AccZ = float.Parse(SplitData[3]);

        lastData = new Vector3(AccX, AccY, AccZ);

        //Vector3 ParseAccelerometerData(string stream);
        /*string Temp = SplitData[4];
        string GyroX = (float.Parse(SplitData[5]) / 10000).ToString();
        string GyroY = (float.Parse(SplitData[6]) / 10000).ToString();
        string GyroZ = (float.Parse(SplitData[7]) / 10000).ToString();*/

        /*Acceleration.text = "X: " + AccX + "\nY: " + AccY + "\nZ: " + AccZ;
        Gyroscope.text = "X: " + GyroX + "\nY: " + GyroY + "\nZ: " + GyroZ;
        Magnetometer.text = "X: " + MagX + "\nY: " + MagY + "\nZ: " + MagZ;
        Temperature.text = Temp + "`C";

        posX += float.Parse(GyroX);
        posY += float.Parse(GyroY);
        posZ += float.Parse(GyroZ);

        sensX += float.Parse(AccX);
        sensY += float.Parse(AccY);
        sensZ += float.Parse(AccZ);*/

        //Vector3 accl = ParseAccelerometerData(stream);
        //Smoothly rotate to the new rotation position.
        t.transform.rotation = Quaternion.Slerp(t.transform.rotation, Quaternion.Euler(lastData), Time.deltaTime * 2f);

    }
}