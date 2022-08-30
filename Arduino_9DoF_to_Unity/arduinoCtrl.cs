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
    // replace with your board's COM port
    SerialPort stream = new SerialPort("COM52", 9600);

    public Transform t;

    void Start()
    {
        stream.Open();
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

        t.transform.rotation = Quaternion.Slerp(t.transform.rotation, Quaternion.Euler(lastData), Time.deltaTime * 2f);

    }
}